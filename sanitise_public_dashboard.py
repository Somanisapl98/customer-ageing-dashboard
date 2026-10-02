from pathlib import Path
import json
ROOT=Path(r"C:\Users\sande\OneDrive - Somanigrp\Ageing Dashboard")
src=ROOT/"Dashboard"/"dashboard-data.json";out=ROOT/"GitHub Public"/"dashboard-public-data.json"
def mask(name):
 words=str(name).split();return " ".join(w[:2]+"*"*max(1,len(w)-2) for w in words[:4])
def band(d):
 d=float(d or 0);return "No ageing" if d<=0 else "1-30 days" if d<=30 else "31-60 days" if d<=60 else "61-90 days" if d<=90 else "90+ days"
p=json.loads(src.read_text(encoding="utf-8"));safe=[]
for c in p.get("customers",[]):safe.append({"Code":str(c.get("Code",""))[:3]+"***","Customer":mask(c.get("Customer","")),"Utilisation_Percent":round(float(c.get("Utilisation_Percent",0)),2),"Ageing_Band":band(c.get("Oldest_Days",0)),"Alert_Level":c.get("Alert_Level","Normal")})
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({"updatedAt":p.get("updatedAt"),"summary":p.get("summary",{}),"customers":safe},indent=2),encoding="utf-8");print(f"Created: {out}")