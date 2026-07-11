from fastapi import APIRouter
from app.api.v1.admin.dashboard import router as dashboard_router
from app.api.v1.admin.inventory import router as inventory_router
from app.api.v1.admin.suppliers import router as suppliers_router
from app.api.v1.admin.members import router as members_router
from app.api.v1.admin.cooperatives import router as cooperatives_router
from app.api.v1.admin.finance import router as finance_router
from app.api.v1.admin.village import router as village_router
from app.api.v1.admin.knowledge import router as knowledge_router
from app.api.v1.admin.users import router as users_router
from app.api.v1.admin.notifications import router as notifications_router
from app.api.v1.admin.recommendations import router as recommendations_router
from app.api.v1.admin.export import router as export_router
from app.api.v1.admin.transactions import router as transactions_router
from app.api.v1.admin.loans import router as loans_router
from app.api.v1.admin.pos import router as pos_router
from app.api.v1.admin.chathub import router as chathub_router
from app.api.v1.admin.automations import router as automations_router
from app.api.v1.admin.ops import router as ops_router
from app.api.v1.admin.network_supply import router as network_supply_router
from app.api.v1.admin.shu import router as shu_router
from app.api.v1.admin.analytics import router as analytics_router
from app.api.v1.admin.review import router as review_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(analytics_router)
router.include_router(review_router)
router.include_router(inventory_router)
router.include_router(suppliers_router)
router.include_router(members_router)
router.include_router(cooperatives_router)
router.include_router(finance_router)
router.include_router(village_router)
router.include_router(knowledge_router)
router.include_router(users_router)
router.include_router(notifications_router)
router.include_router(recommendations_router)
router.include_router(export_router)
router.include_router(transactions_router)
router.include_router(loans_router)
router.include_router(pos_router)
router.include_router(chathub_router)
router.include_router(automations_router)
router.include_router(ops_router)
router.include_router(network_supply_router)
router.include_router(shu_router)
