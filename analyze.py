from pathlib import Path
from decimal import Decimal
from collections import defaultdict, Counter
import openpyxl, json, csv, hashlib

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'validation' / 'python'
OUT.mkdir(parents=True,exist_ok=True)
SRC = ROOT / 'База данных_основная.xlsx'
w = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
def rows(s): return [list(r) for r in list(w[s].values)[1:] if any(v is not None for v in r)]
def num(x): return Decimal(str(x).replace('\xa0','').replace(' ','').replace(',','.'))
dates = dict(rows('СПР_даты_заказа'))
products = {r[2]:r[:2] for r in rows('СПР_продукты')}
managers = dict(rows('СПР_Менеджеры'))
shipping = dict(rows('СПР_стоимость_доставки'))
segments = defaultdict(set)
for c,s in rows('СПР_покупатели'): segments[c].add(s)
conflicts = {c:sorted(v) for c,v in segments.items() if len(v)>1}
facts=[]
for i,r in enumerate(rows('Продажи'),2):
    oid,priority,qty,rev,method,profit,buyer,region,product,pack=r
    assert oid in dates and product in products and buyer in segments and region in managers and method in shipping
    facts.append(dict(Row=i,Order_ID=oid,Date=dates[oid].strftime('%Y-%m-%d'),Priority=priority,Quantity=qty,
        Revenue=float(num(rev)),Profit=float(num(profit)),Shipping=shipping[method],Method=method,Buyer=buyer,
        Region=region,Manager=managers[region],Product=str(product),Category=products[product][0],Subcategory=products[product][1],
        Segment=next(iter(segments[buyer])) if len(segments[buyer])==1 else 'Неоднозначный сегмент',Package=pack))

def metrics(rs):
    rev=sum(Decimal(str(r['Revenue'])) for r in rs);profit=sum(Decimal(str(r['Profit'])) for r in rs)
    ids={r['Order_ID'] for r in rs}
    return dict(Revenue=float(rev),Profit=float(profit),Margin=float(profit/rev) if rev else None,
        Customers=len({r['Buyer'] for r in rs}),Orders=len(ids),AOV=float(rev/len(ids)) if ids else None,
        Shipping=sum(r['Shipping'] for r in rs),Lines=len(rs))
def group(field):
    g=defaultdict(list)
    for r in facts:g[r[field]].append(r)
    return [{field:k,**metrics(v)} for k,v in sorted(g.items())]

orders=defaultdict(list)
for r in facts:orders[r['Order_ID']].append(r)
negative=[oid for oid,v in orders.items() if sum(Decimal(str(r['Profit'])) for r in v)<0]
mgr=[]
for m in sorted(set(managers.values())):
    rs=[r for r in facts if r['Manager']==m];og=defaultdict(list)
    for r in rs:og[r['Order_ID']].append(r)
    bad={oid for oid,v in og.items() if sum(Decimal(str(r['Profit'])) for r in v)<0}
    losses=[r for r in rs if r['Order_ID'] in bad]
    mgr.append(dict(Manager=m,NegativeOrders=len(bad),NegativeProfit=metrics(losses)['Profit'],**metrics(rs)))
abc=sorted(group('Product'),key=lambda r:(-r['Revenue'],r['Product']))
cum=Decimal(0);total=sum(num(r['Revenue']) for r in facts)
for i,r in enumerate(abc,1):
    previous=cum/total;cum+=num(r['Revenue'])
    r.update(Rank=i,Share=float(num(r['Revenue'])/total),Cumulative=float(cum/total),ABC='A' if previous<Decimal('.8') else ('B' if previous<Decimal('.95') else 'C'))
abc_summary=[]
for c in 'ABC':
    names={r['Product'] for r in abc if r['ABC']==c}
    abc_summary.append(dict(ABC=c,Products=len(names),**metrics([r for r in facts if r['Product'] in names])))

audit=dict(Source=SRC.name,SHA256=hashlib.sha256(SRC.read_bytes()).hexdigest(),
    ConflictingCustomers=conflicts,ConflictingCustomerCount=len(conflicts),
    AmbiguousSegment=metrics([r for r in facts if r['Segment']=='Неоднозначный сегмент']),
    OrderMethodConflicts=sum(len({r['Method'] for r in v})>1 for v in orders.values()),
    OrderRegionConflicts=sum(len({r['Region'] for r in v})>1 for v in orders.values()),
    NegativeLines=sum(r['Profit']<0 for r in facts),OrdersAnyNegativeLine=sum(any(r['Profit']<0 for r in v) for v in orders.values()),
    NegativeOrders=len(negative),NegativeProfit=metrics([r for r in facts if r['Order_ID'] in negative])['Profit'],
    Dates=[min(r['Date'] for r in facts),max(r['Date'] for r in facts)],
    ScreenshotRevenue=1097087.92,RevenueDifference=float(total-Decimal('1097087.92')),
    EmptyRowsSales=w['Продажи'].max_row-1-len(facts),
    DictionaryRows={s:len(rows(s)) for s in w.sheetnames if s!='Продажи'})
data=dict(facts=facts,summary=metrics(facts),months=group('Date'),segments=group('Segment'),managers=mgr,
    regions=group('Region'),abc=abc,abc_summary=abc_summary,audit=audit)
# Exact source controls and conservation checks.
assert len(facts)==730 and len(orders)==571 and len({r['Product'] for r in facts})==445
assert total==Decimal('1103256.31') and sum(num(r['Profit']) for r in facts)==Decimal('253784.61')
assert sum(num(r['Revenue']) for r in abc)==total
assert sum(num(r['Revenue']) for r in abc_summary)==total
assert len({r['Row'] for r in facts})==len(facts)
assert abs(abc[-1]['Cumulative']-1)<1e-12
(OUT/'analysis.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
for name,rs in [('Продажи очищенные',facts),('ABC номенклатуры',abc),('Убыточные заказы по менеджерам',mgr),('Сегменты',data['segments']),('Регионы',data['regions'])]:
    with (OUT/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rs[0]),delimiter=';');writer.writeheader();writer.writerows(rs)
print(json.dumps({k:v for k,v in data.items() if k in ['summary','audit','abc_summary','managers']},ensure_ascii=False,indent=2))
