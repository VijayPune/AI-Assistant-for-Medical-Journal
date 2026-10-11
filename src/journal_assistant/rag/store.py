"""SQLite FTS5 plus a local float-vector table for the POC index."""
from __future__ import annotations

import json
import math
import sqlite3
import struct
from pathlib import Path

from .env import ROOT

class SQLiteHybridStore:
    def __init__(self,path:Path|None=None):
        self.path=path or ROOT/"data/indexes/journal_assistant.sqlite3"
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path)
        self.db.row_factory=sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS chunks(
            chunk_id TEXT PRIMARY KEY, article_id TEXT NOT NULL, title TEXT NOT NULL,
            authors TEXT NOT NULL, section TEXT NOT NULL, content_role TEXT NOT NULL,
            year INTEGER NOT NULL, month INTEGER NOT NULL, volume INTEGER NOT NULL,
            issue_number INTEGER NOT NULL, issue_id TEXT NOT NULL, page_start TEXT,
            page_end TEXT, physical_page INTEGER NOT NULL, page_role TEXT NOT NULL,
            source_filename TEXT NOT NULL, source_sha256 TEXT NOT NULL, source_url TEXT NOT NULL,
            text TEXT NOT NULL, embedding BLOB, embedding_dimensions INTEGER,
            embedding_model TEXT, metadata_json TEXT NOT NULL)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_article ON chunks(article_id)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_filters ON chunks(year,volume,issue_number,section,content_role)")
        self.db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5(
            chunk_id UNINDEXED,title,authors,section,search_text, tokenize='porter unicode61')""")
        self.db.commit()

    def close(self): self.db.close()

    def reset(self):
        self.db.execute("DELETE FROM chunks")
        self.db.execute("DELETE FROM chunk_fts")
        self.db.commit()

    def upsert_chunks(self,chunks:list[dict],vectors:list[list[float]]|None=None,embedding_model:str|None=None):
        if vectors is not None and len(vectors)!=len(chunks):
            raise ValueError("Each chunk must have exactly one embedding")
        with self.db:
            for i,item in enumerate(chunks):
                vector=vectors[i] if vectors is not None else None
                blob=struct.pack(f"{len(vector)}f",*vector) if vector else None
                dimensions=len(vector) if vector else None
                metadata={k:v for k,v in item.items() if k!="text"}
                self.db.execute("""INSERT OR REPLACE INTO chunks VALUES
                    (:chunk_id,:article_id,:title,:authors,:section,:content_role,:year,:month,:volume,
                     :issue_number,:issue_id,:page_start,:page_end,:physical_page,:page_role,
                     :source_filename,:source_sha256,:source_url,:text,:embedding,:dimensions,:model,:metadata)""",
                    {**item,"embedding":blob,"dimensions":dimensions,"model":embedding_model,"metadata":json.dumps(metadata,ensure_ascii=False)})
                self.db.execute("DELETE FROM chunk_fts WHERE chunk_id=?",(item["chunk_id"],))
                self.db.execute("INSERT INTO chunk_fts(chunk_id,title,authors,section,search_text) VALUES(?,?,?,?,?)",
                    (item["chunk_id"],item["title"],item.get("authors", ""),item["section"],item["text"]))

    def counts(self)->dict[str,int]:
        row=self.db.execute("SELECT COUNT(*) n,SUM(CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END) v FROM chunks").fetchone()
        return {"chunks":int(row["n"] or 0),"vectors":int(row["v"] or 0)}

    def _matches(self,row:sqlite3.Row,allowed_roles:set[str]|None,filters:dict|None)->bool:
        if allowed_roles and row["content_role"] not in allowed_roles:return False
        f=filters or {}
        exact={"year":"year","volume":"volume","issue_number":"issue_number","section":"section","issue_id":"issue_id","article_id":"article_id"}
        for key,col in exact.items():
            if key in f:
                value=f[key]
                if isinstance(value,(list,tuple,set)):
                    if str(row[col]).casefold() not in {str(x).casefold() for x in value}:return False
                elif str(row[col]).casefold()!=str(value).casefold():return False
        if "author" in f and str(f["author"]).casefold() not in str(row["authors"]).casefold():return False
        if "year_from" in f and row["year"]<int(f["year_from"]):return False
        if "year_to" in f and row["year"]>int(f["year_to"]):return False
        return True

    def lexical_search(self,query:str,*,limit:int=80,allowed_roles:set[str]|None=None,filters:dict|None=None)->list[dict]:
        import re
        terms=[]
        for word in re.findall(r"[\w]+",query,flags=re.UNICODE):
            if len(word)>1:terms.append('"'+word.replace('"','""')+'"')
        if not terms:return []
        match=" OR ".join(terms)
        rows=self.db.execute("SELECT c.*,bm25(chunk_fts,0,2.0,2.5,1.4,1.0) AS lexical_rank FROM chunk_fts JOIN chunks c ON c.chunk_id=chunk_fts.chunk_id WHERE chunk_fts MATCH ? ORDER BY lexical_rank LIMIT ?",(match,limit)).fetchall()
        return [self._row_to_dict(r)|{"lexical_rank":float(r["lexical_rank"])} for r in rows if self._matches(r,allowed_roles,filters)]

    def vector_search(self,vector:list[float],*,limit:int=80,allowed_roles:set[str]|None=None,filters:dict|None=None)->list[dict]:
        rows=self.db.execute("SELECT * FROM chunks WHERE embedding IS NOT NULL").fetchall()
        qnorm=math.sqrt(sum(x*x for x in vector)) or 1.0
        ranked=[]
        for row in rows:
            if not self._matches(row,allowed_roles,filters):continue
            dims=row["embedding_dimensions"]
            if not dims or dims!=len(vector):continue
            vals=struct.unpack(f"{dims}f",row["embedding"])
            dot=sum(a*b for a,b in zip(vals,vector));norm=math.sqrt(sum(x*x for x in vals)) or 1.0
            ranked.append((dot/(norm*qnorm),self._row_to_dict(row)))
        ranked.sort(key=lambda x:x[0],reverse=True)
        return [item|{"semantic_similarity":score} for score,item in ranked[:limit]]

    @staticmethod
    def _row_to_dict(row):
        out={k:row[k] for k in row.keys() if k not in {"embedding","embedding_dimensions","embedding_model","metadata_json"}}
        out["metadata"]=json.loads(row["metadata_json"])
        return out

def reciprocal_rank_fusion(lexical:list[dict],semantic:list[dict],*,top_k:int=6,rrf_k:int=60,secondary_multiplier:float=.75,max_per_article:int=2)->list[dict]:
    combined={}
    for source,rank_key in ((lexical,"lexical_rank"),(semantic,"semantic_similarity")):
        for rank,item in enumerate(source,start=1):
            entry=combined.setdefault(item["chunk_id"],dict(item,hybrid_score=0.0,lexical_rank=None,semantic_similarity=None))
            entry["hybrid_score"]+=1.0/(rrf_k+rank)
            entry[rank_key]=item.get(rank_key)
    results=sorted(combined.values(),key=lambda x:x["hybrid_score"],reverse=True)
    chosen=[]; counts={}
    for item in results:
        multiplier=secondary_multiplier if item["content_role"]=="secondary_source" else 1.0
        item["hybrid_score"]*=multiplier
        n=counts.get(item["article_id"],0)
        if n>=max_per_article:continue
        counts[item["article_id"]]=n+1;chosen.append(item)
        if len(chosen)>=top_k:break
    return chosen
