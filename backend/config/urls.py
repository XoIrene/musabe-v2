from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from core import views as core
from core import reports
from inventory import views as inv
from procurement.views import RequestViewSet
from students import views as stu
from academics import views as acad
from fees import views as fees
from transport import views as trans
from announcements.views import AnnouncementViewSet

router = DefaultRouter()
router.register('branches', core.BranchViewSet)
router.register('staff', core.StaffViewSet)
router.register('audit', core.AuditViewSet)
router.register('requests', RequestViewSet, basename='request')
router.register('items', inv.ItemViewSet)
router.register('copies', inv.CopyViewSet)
router.register('issues', inv.IssueViewSet)
router.register('writeoffs', inv.WriteOffViewSet)
router.register('contributions', inv.ContributionViewSet)
router.register('movements', inv.MovementViewSet)
router.register('classes', stu.ClassRoomViewSet, basename='classroom')
router.register('students', stu.StudentViewSet, basename='student')
router.register('guardians', stu.GuardianViewSet, basename='guardian')
router.register('subjects', acad.SubjectViewSet, basename='subject')
router.register('terms', acad.TermViewSet, basename='term')
router.register('assessments', acad.AssessmentViewSet, basename='assessment')
router.register('attendance', acad.AttendanceViewSet, basename='attendance')
router.register('fees', fees.FeeViewSet, basename='fee')
router.register('invoices', fees.InvoiceViewSet, basename='invoice')
router.register('routes', trans.RouteViewSet, basename='route')
router.register('transport', trans.AssignmentViewSet, basename='transport')
router.register('announcements', AnnouncementViewSet, basename='announcement')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', core.LoginView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
    path('api/me/', core.me),
    path('api/reports/summary/', inv.summary),
    path('api/reports/student/<int:pk>/', acad.student_report),
    path('api/reports/<str:name>/', reports.report),
    path('api/', include(router.urls)),
]
