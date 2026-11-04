from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json, re
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]; INPUT=ROOT/'input'; DATA=ROOT/'data'; LOGS=ROOT/'logs'
AGING=INPUT/'Customer Aging Analyses Bill To Bill.xlsx'; MASTER=INPUT/'Customer Master.xlsx'; OUTPUT=DATA/'dashboard-data.json'
DATA.mkdir(exist_ok=True);LOGS.mkdir(exist_ok=True)
def txt(v): return '' if v is None else str(v).strip()
def key(v): return re.sub(r'[^A-Z0-9]','',txt(v).upper())
def head(v): return re.sub(r'[^a-z0-9]','',txt(v).lower())
def num(v):
    if isinstance(v,(int,float)): return float(v)
    try:return float(txt(v).replace('₹','').replace(',','').replace('(','-').replace(')',''))
    except:return None
def header(ws,groups):
    for r in range(1,min(ws.max_row,50)+1):
        h={head(ws.cell(r,c).value):c for c in range(1,ws.max_column+1)}
        if all(any(head(a) in h for a in g) for g in groups):return r,h
    return None,{}
def col(h,*a):
    for x in a:
        if head(x) in h:return h[head(x)]

def read_master():
    wb=load_workbook(MASTER,data_only=True);ws=wb.active
    r,h=header(ws,[("Code",),("Customer",),("Sales Executive","Salesman")])
    if not r: raise ValueError('Customer Master header not found')
    cc=col(h,'Code');cn=col(h,'Customer');cs=col(h,'Sales Executive','Salesman');cp=col(h,'Contact_Person','Contact Person');cd=col(h,'Cr Days');cl=col(h,'Cr_Limit');cu=col(h,'Used_Cr_Limit');cr=col(h,'Rem_Cr_Limit');cg=col(h,'GST Category')
    out={}
    for i in range(r+1,ws.max_row+1):
        code=txt(ws.cell(i,cc).value);name=txt(ws.cell(i,cn).value)
        if code and name:out[key(code)]={'Customer':name,'MasterSalesman':txt(ws.cell(i,cs).value),'ContactPerson':txt(ws.cell(i,cp).value) if cp else '','CreditDays':int(num(ws.cell(i,cd).value) or 0) if cd else 0,'CreditLimit':num(ws.cell(i,cl).value) or 0,'UsedCredit':num(ws.cell(i,cu).value) or 0,'RemainingCredit':num(ws.cell(i,cr).value) or 0,'GSTCategory':txt(ws.cell(i,cg).value) if cg else ''}
    wb.close();print(f'Loaded {len(out)} customers from Customer Master');return out

def main():
    master=read_master();wb=load_workbook(AGING,data_only=True);ws=wb.active
    r,h=header(ws,[("party_code",),("Outstanding_Amt",),("Days",)])
    if not r:raise ValueError('Aging detail header not found')
    cb=col(h,'Branch');cbi=col(h,'Bill No');cc=col(h,'party_code');co=col(h,'Outstanding_Amt');cd=col(h,'Days');cs=col(h,'salesman_name')
    groups=defaultdict(lambda:{'Code':'','Customer':'','Outstanding':0.0,'AgeingDays':0,'OpenBills':0,'Branch':'','parts':defaultdict(lambda:{'Outstanding':0.0,'OpenBills':0,'OldestDays':0})});current=''
    for i in range(r+1,ws.max_row+1):
        first=txt(ws.cell(i,1).value)
        if first.lower().startswith('customer:'):current=first.split(':',1)[1].strip();continue
        code=txt(ws.cell(i,cc).value);bill=txt(ws.cell(i,cbi).value);amount=num(ws.cell(i,co).value);days=num(ws.cell(i,cd).value)
        if not code or not bill or amount is None or days is None:continue
        k=key(code);g=groups[k];g['Code']=code;g['Customer']=current or master.get(k,{}).get('Customer',code);g['Outstanding']+=amount;g['AgeingDays']=max(g['AgeingDays'],int(days));g['OpenBills']+=1;g['Branch']=txt(ws.cell(i,cb).value) if cb else ''
        salesman=txt(ws.cell(i,cs).value) or 'Unassigned';p=g['parts'][salesman];p['Outstanding']+=amount;p['OpenBills']+=1;p['OldestDays']=max(p['OldestDays'],int(days))
    wb.close();customers=[]
    for k,g in groups.items():
        m=master.get(k,{});parts=[{'Salesman':n,'Outstanding':round(v['Outstanding'],2),'OpenBills':v['OpenBills'],'OldestDays':v['OldestDays']} for n,v in sorted(g.pop('parts').items(),key=lambda x:x[0].casefold())]
        active=[p['Salesman'] for p in parts if abs(p['Outstanding'])>.005];days=g['AgeingDays'];g['Outstanding']=round(g['Outstanding'],2);g['SalesmanBreakdown']=parts;g['Salesman']=active[0] if len(active)==1 else 'Multiple' if active else m.get('MasterSalesman','');g['AgeingBand']='0-30' if days<=30 else '31-60' if days<=60 else '61-90' if days<=90 else '90+'
        for f in ['ContactPerson','CreditDays','CreditLimit','UsedCredit','RemainingCredit','GSTCategory']:g[f]=m.get(f,'' if f in ['ContactPerson','GSTCategory'] else 0)
        g['Mobile']='';customers.append(g)
    customers.sort(key=lambda x:x['Customer'].casefold());payload={'updatedAt':datetime.now().astimezone().isoformat(timespec='seconds'),'summary':{'customers':len(customers),'outstanding':round(sum(x['Outstanding'] for x in customers),2),'above30':sum(x['AgeingDays']>30 for x in customers),'above60':sum(x['AgeingDays']>60 for x in customers)},'customers':customers};OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Created {OUTPUT} with {len(customers)} customers');print(f"Total outstanding: {payload['summary']['outstanding']:.2f}")
if __name__=='__main__':main()
