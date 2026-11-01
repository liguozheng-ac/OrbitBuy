"""固定混淆候选的工具边界回归；第二个参数可指定只读基线源码目录。"""
import asyncio, hashlib, json, sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT
sys.path.insert(0, str(SOURCE))
from app.application.usecases.catalog_search import CatalogSearchUseCase
from app.domain.catalog.product_search_spec import ProductSearchSpec
from app.domain.catalog.product import Product
from app.domain.catalog.sku import Sku
from app.domain.catalog.money import Money
from app.domain.catalog.ports.retrieval_ports import VectorHit
from app.infrastructure.persistence.in_memory_repositories import InMemoryProductRepository
from app.application.tools.product_search_tool import build_product_search_tool
from app.infrastructure.eventbus import TradeEventBus

# 固定的合成事实和人工相关标签；高分混淆项专门检验类型约束，不代表线上效果。
FACTS = [
    ('P9101', 'TravelScale 背包出行行李秤', None, 30, .15),
    ('P9102', 'Travel 腰包', '腰包', 60, .2),
    ('P9103', 'Trail Backpack', '背包', 180, .4),
    ('P9104', 'City 双肩包', '背包', 260, .7),
    ('P9105', 'Backpack Rain Cover', None, 20, .05),
    ('P9106', 'Travel Neck Pillow', '颈枕', 80, .3),
    ('P9107', 'Quiet Headphones', '耳机', 190, .25),
]
CASES = [
    dict(id='zh-type', query='旅行背包', kind='背包', gold=['P9103','P9104']),
    dict(id='en-type', query='travel backpack', kind='背包', gold=['P9103','P9104']),
    dict(id='ja-type', query='旅行用のリュック', kind='背包', gold=['P9103','P9104']),
    dict(id='budget', query='旅行背包', kind='背包', price_max_major=200, gold=['P9103']),
    dict(id='landed', query='旅行背包', kind='背包', price_max_major=200, price_basis='landed', ship_to='CN', gold=[]),
    dict(id='weight', query='旅行背包', kind='背包', max_weight_kg=.5, gold=['P9103']),
    dict(id='empty', query='旅行背包', kind='背包', price_max_major=10, gold=[]),
    dict(id='pillow', query='neck pillow', kind='颈枕', gold=['P9106']),
    dict(id='headphones', query='headphones', kind='耳机', gold=['P9107']),
]
async def main():
    products=[Product(product_id=pid,title=title,brand='Fixture',category='旅行装备',origin_country='CN',
        product_type=kind or '未知类型',weight_kg=weight,ships_to=['CN'],description='旅行背包 neck pillow headphones',
        skus=[Sku(pid+'-S1','标准',Money.from_major_units(price,'CNY'),5)]) for pid,title,kind,price,weight in FACTS]
    service=CatalogSearchUseCase(InMemoryProductRepository(products),
        embedder=SimpleNamespace(embed=AsyncMock(return_value=[1])),
        vector_index=SimpleNamespace(search=AsyncMock(return_value=[VectorHit(p.product_id,1-i*.01) for i,p in enumerate(products)])))
    rows=[]
    tool=build_product_search_tool(service,TradeEventBus())
    for case in CASES:
        args={k:v for k,v in case.items() if k in {'price_max_major','max_weight_kg','ship_to','price_basis'}}
        # 基线旧合同尚无 price_basis：如实记录它只按商品价过滤。
        if 'price_basis' not in ProductSearchSpec.__dataclass_fields__: args.pop('price_basis',None)
        chunk=await tool(normalized_query=case['query'],top_k=5,**args)
        result=json.loads(chunk.content[0].text)
        ids=[h['product_id'] for h in result['hits']]; gold=set(case['gold']); valid=set(ids)&gold
        rows.append({'id':case['id'],'expected':sorted(gold),'returned':ids,
            'precision':len(valid)/len(ids) if ids else (1 if not gold else 0),
            'recall':len(valid)/len(gold) if gold else None,'violations':len(set(ids)-gold)})
    paths=['app/domain/catalog/product_attributes.py','app/domain/catalog/product_search_spec.py',
           'app/application/tools/product_search_tool.py','app/application/usecases/catalog_search.py']
    data={'scope':'固定合成工具合同，非生产质量结论','source_files':{p:hashlib.sha256((SOURCE/p).read_bytes()).hexdigest() for p in paths},
        'fixture_sha256':hashlib.sha256(json.dumps([FACTS,CASES],ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
        'rows':rows,'macro_precision':sum(r['precision'] for r in rows)/len(rows),
        'positive_macro_recall':sum(r['recall'] for r in rows if r['recall'] is not None)/sum(r['recall'] is not None for r in rows),
        'violation_count':sum(r['violations'] for r in rows)}
    path=Path(sys.argv[1]);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as handle:json.dump(data,handle,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in data.items() if k!='rows'},ensure_ascii=False))
asyncio.run(main())
