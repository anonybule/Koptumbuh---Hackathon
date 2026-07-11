"""Mobile API routers for KopTumbuh operator / anggota apps."""

from app.api.v1.mobile.dashboard import router as dashboard_router
from app.api.v1.mobile.products import router as products_router
from app.api.v1.mobile.transactions import router as transactions_router
from app.api.v1.mobile.restock import router as restock_router
from app.api.v1.mobile.members import router as members_router
from app.api.v1.mobile.customers import router as customers_router
from app.api.v1.mobile.savings import router as savings_router
from app.api.v1.mobile.recommendations import router as recommendations_router
from app.api.v1.mobile.messages import router as messages_router
from app.api.v1.mobile.notifications import router as notifications_router
from app.api.v1.mobile.profile import router as profile_router
from app.api.v1.mobile.member_self import router as member_self_router
from app.api.v1.mobile.deliveries import router as deliveries_router
from app.api.v1.mobile.knowledge import router as knowledge_router

MOBILE_ROUTERS = [
    dashboard_router,
    products_router,
    transactions_router,
    restock_router,
    members_router,
    customers_router,
    savings_router,
    recommendations_router,
    messages_router,
    notifications_router,
    profile_router,
    member_self_router,
    deliveries_router,
    knowledge_router,
]

__all__ = ["MOBILE_ROUTERS"]
