"""检索请求合同：保留预算、类型、候选数量与结果替换的回归检查。"""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.application.usecases.catalog_search import CatalogSearchUseCase
from app.domain.catalog.product_search_spec import ProductSearchSpec
from app.infrastructure.persistence.in_memory_repositories import InMemoryProductRepository
from tests.test_retrieval_algorithm_contracts import _product, _sku, _search


async def _search_snapshot(**conditions):
    args=dict(normalized_query='旅行背包',ship_to='CN',price_max_major=300,target_currency='CNY',price_basis='item',product_type='背包')
    args.update(conditions)
    spec=ProductSearchSpec(**args)
    result=await CatalogSearchUseCase(InMemoryProductRepository([
        _product(1001,weight=.6,skus=[_sku('P1001',1,'黑色 20L',180)]),
        _product(1002,weight=.3,skus=[_sku('P1002',1,'黑色 20L',220)]),
    ])).execute(spec)
    result['query_conditions']={**args,'product_type':spec.product_type}
    result['observed_at']='2026-10-30T00:00:00Z'
    return {'data': result}



@pytest.mark.parametrize('path',['keyword','dense','hybrid'])
async def test_landed_filter_uses_same_sku_and_keeps_unknown_quote_out(path):
    item=_product(skus=[_sku('P1001',1,'红色',180),_sku('P1001',2,'黑色',170)])
    service,_=_search([item],path=path)
    found=await service.execute(ProductSearchSpec(normalized_query='背包',ship_to='CN',price_max_major=200,price_basis='landed'))
    assert found['hits'][0]['default_sku_id']=='P1001-S2'
    assert found['hits'][0]['landed_price']['landed_total_major']==195
    assert found['hits'][0]['eligible_sku_ids']==['P1001-S2']
    unknown=await service.execute(ProductSearchSpec(normalized_query='背包',ship_to='XX',price_max_major=200,price_basis='landed'))
    assert unknown['hits']==[]



def test_landed_requires_destination_and_valid_basis():
    with pytest.raises(ValueError): ProductSearchSpec(normalized_query='背包',price_basis='landed')
    with pytest.raises(ValueError): ProductSearchSpec(normalized_query='背包',price_basis='guess')



@pytest.mark.parametrize('query,kind', [('通勤背包','背包'),('travel backpack','背包'),('旅行用のリュック','背包'),
    ('neck pillow','颈枕'),('ネックピロー','颈枕'),('backpack rain cover',None),('不要背包',None),
    ('no backpack',None),('リュックはいらない',None),('背包和颈枕',None),('旅行装备',None),
    ('背包旅行用的行李秤',None),('patch for backpack',None),('リュックのカバー',None)])
def test_only_single_positive_type_is_inferred(query,kind):
    from app.domain.catalog.product_attributes import infer_requested_product_type
    assert infer_requested_product_type(query)==kind



async def test_tool_normalizes_type_before_category_and_publishes_conditions():
    from app.application.tools.product_search_tool import build_product_search_tool
    from app.infrastructure.eventbus import TradeEventBus
    source=await _search_snapshot()
    service=SimpleNamespace(execute=AsyncMock(return_value=source['data']))
    bus=TradeEventBus();events=[]
    from app.infrastructure.eventbus import observe_run_events
    with observe_run_events(events.append):
        await build_product_search_tool(service,bus)(normalized_query='户外背包',ship_to='CN',price_max_major=200,price_basis='landed')
    spec=service.execute.call_args.args[0]
    assert spec.product_type=='背包' and spec.category is None and spec.price_basis=='landed'
    payload=next(e.payload for e in events if e.type=='tool.result')
    assert payload['query_conditions']['product_type']=='背包' and payload['observed_at']



async def test_user_candidate_limit_controls_tool_result_and_does_not_leak_context():
    from app.application.tools.product_search_tool import build_product_search_tool
    from app.infrastructure.eventbus import TradeEventBus
    from app.infrastructure.context import ShoppingContext, ShoppingContextSnapshot
    source=await _search_snapshot()
    service=SimpleNamespace(execute=AsyncMock(return_value=source['data']))
    tool=build_product_search_tool(service,TradeEventBus())
    token=ShoppingContext.set(ShoppingContextSnapshot('s','buyer','zh-CN','CNY',candidate_limit=2))
    try:
        await tool(normalized_query='背包',top_k=10)
        assert service.execute.call_args.args[0].top_k==2
    finally: ShoppingContext.reset(token)
    await tool(normalized_query='背包',top_k=10)
    assert service.execute.call_args.args[0].top_k==10



@pytest.mark.parametrize('query',['最多2款背包','找2款背包','up to 2 backpacks','最大2点のリュック'])
async def test_display_limit_survives_model_over_recall_and_preserves_snapshot(query):
    from app.application.agents.product_candidate_projection import ProductCandidateProjection
    projection=ProductCandidateProjection(query)
    source=await _search_snapshot()
    hits=source['data']['hits']+[dict(source['data']['hits'][0],product_id='P1003')]
    projection.apply({'tool':'product_search_tool','hits':hits,'query_conditions':{'top_k':10}})
    assert len(projection.result['hits'])==2 and projection.result['display_limit']==2
    assert len(hits)==3



async def test_exact_id_projection_does_not_merge_different_budget_snapshots():
    from app.application.agents.product_candidate_projection import ProductCandidateProjection
    projection=ProductCandidateProjection('比较 P1001 和 P1002')
    source=await _search_snapshot()
    for number, cap in [(0,300),(1,250)]:
        projection.apply({'tool':'product_search_tool','hits':[source['data']['hits'][number]],
            'recall_strategy':'exact_id_lookup','query_conditions':{'price_max_major':cap}})
    assert [p['product_id'] for p in projection.result['hits']]==['P1002']
