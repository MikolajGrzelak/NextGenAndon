from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from core import views
from core.views import (
    index_view,
    upload_plan, 
    upload_status,
    plan_na_dzis,
    manufacturing_orders_menu,
    logout_success,
    register_scrap, 
    register_scrap_success,
    get_items_by_group,
    get_item_details,
    warehouse_tickets, 
    warehouse_ticket_detail, 
    update_warehouse_status,
    call_warehouse,
    get_warehouse_ticket_comments, 
    take_warehouse_ticket,
    close_warehouse_ticket,
    add_warehouse_comment,
    production_plan_view, 
    get_production_plan_data,
    update_order_status,
    get_comments,
    add_comment,
    upload_production_log,
    production_report_view,
    get_production_report_data,
    warehouse_index, 
    cycle_count_requests,
    update_cycle_count_status,
    cycle_count_view,
    get_item_details, 
    check_scrap_code,
    check_location,
    autocomplete_item,
    autocomplete_location,
    cycle_count_report,
    inv_request_list,
    inv_request_create,
    inv_request_detail,
    inv_request_approve,
    inv_request_reject,
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('zlecenia-produkcyjne/', manufacturing_orders_menu, name='manufacturing_orders_menu'),
    path('upload-plan/', views.upload_plan, name='upload_plan'),  # Ścieżka do wgrywania planu produkcji
    path('edit-production-plan/<int:plan_id>/', views.edit_production_plan, name='edit_production_plan'),
    path('upload-status/', upload_status, name='upload_status'),
    path('plan-na-dzis/', plan_na_dzis, name='plan_na_dzis'),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", logout_success, name="logout"),
    path("logout-success/", logout_success, name="logout_success"),
    path("", index_view, name="index"),
    path("production/c2/", views.production_c2, name="production_c2"),
    path("production/rm5/", views.production_rm5, name="production_rm5"),
    path("production/b2b/", views.production_b2b, name="production_b2b"),
    path("production/gaming/", views.production_gaming, name="production_gaming"),
    path("production/scancoin/", views.production_scancoin, name="production_scancoin"),
    path("production/comestero/", views.production_comestero, name="production_comestero"),
    path("daily-panel/", views.daily_panel, name="daily_panel"),
    path("panel/production/", views.index_production, name="index_production"),
    path("panel/leader/", views.index_leader, name="index_leader"),
    path("panel/planner/", views.index_planner, name="index_planner"),
    path("panel/manager/", views.index_manager, name="index_manager"),
    path("call-technician/", views.call_technician, name="call_technician"),
    path("call-quality/", views.call_quality, name="call_quality"),
    path("call-engineer/", views.call_engineer, name="call_engineer"),
    path('display-board/<str:category>/', views.display_board, name='display_board'),
    path("take-ticket/<int:ticket_id>/", views.take_ticket, name="take_ticket"),
    path("close-ticket/<int:ticket_id>/", views.close_ticket, name="close_ticket"),
    path("register-scrap/", views.register_scrap, name="register_scrap"),
    path("register-scrap-success/", register_scrap_success, name="register_scrap_success"),
    path("autocomplete-item/", views.autocomplete_item, name="autocomplete_item"),
    path("get-items/", get_items_by_group, name="get_items_by_group"), 
    path("get-item-details/", get_item_details, name="get_item_details"), 
    path("warehouse-tickets/", warehouse_tickets, name="warehouse_tickets"),
    path("warehouse-ticket/<int:ticket_id>/", warehouse_ticket_detail, name="warehouse_ticket_detail"),
    path("call-warehouse/", call_warehouse, name="call_warehouse"),
    path("warehouse-tickets/", warehouse_tickets, name="warehouse_tickets"),
    path("update-warehouse-status/<int:ticket_id>/<str:status>/", update_warehouse_status, name="update_warehouse_status"),
    path("get-warehouse-comments/<int:ticket_id>/", get_warehouse_ticket_comments, name="get_warehouse_ticket_comments"),
    path("warehouse/take-ticket/<int:ticket_id>/", take_warehouse_ticket, name="take_warehouse_ticket"),
    path("warehouse/close-ticket/<int:ticket_id>/", close_warehouse_ticket, name="close_warehouse_ticket"),
    path("add-warehouse-comment/<int:ticket_id>/", add_warehouse_comment, name="add_warehouse_comment"),
    path('production-plan/', production_plan_view, name='production_plan'),
    path("production-plan-data/", get_production_plan_data, name="production_plan_data"),
    path("update-order-status/<int:plan_id>/", update_order_status, name="update_order_status"),
    path("get-comments/<int:plan_id>/", views.get_comments, name="get_comments"),
    path("add-comment/<int:plan_id>/", views.add_comment, name="add_comment"),
    path("upload-production-log/", upload_production_log, name="upload_production_log"),
    path("production-report/", production_report_view, name="production_report"),
    path("api/production-report-data/", get_production_report_data, name="production_report_data"),  # 🔹 Dodajemy URL dla AJAX
    path("warehouse/", warehouse_index, name="warehouse_index"),
    path('inv-requests/', views.inv_request_list, name='inv_request_list'),
    path('inv-requests/new/', views.inv_request_create, name='inv_request_create'),
    path('inv-requests/preview/', views.inv_request_preview, name='inv_request_preview'),
    path('inv-requests/submit/', views.inv_request_submit, name='inv_request_submit'),
    path('inv-requests/<int:req_id>/', views.inv_request_detail, name='inv_request_detail'),
    path('inv-requests/<int:req_id>/approve/', views.inv_request_approve, name='inv_request_approve'),
    path('inv-requests/<int:req_id>/reject/', views.inv_request_reject, name='inv_request_reject'),
    path('inv-requests/<int:req_id>/cancel/', views.inv_request_cancel, name='inv_request_cancel'),
    path('get-production-report-data/', views.get_production_report_data, name='get_production_report_data'),


    # 📌 Cycle Count (kontrola stanów magazynowych)
    path("cycle-count/", cycle_count_view, name="cycle_count_view"),  # Lista zgłoszeń
    path("cycle-count/new/", cycle_count_requests, name="cycle_count_requests"),  # Tworzenie nowego zgłoszenia
    path("cycle-count/update-status/<int:request_id>/<str:status>/", update_cycle_count_status, name="update_cycle_count_status"),  # Aktualizacja statusu
    path("cycle-count/report/", cycle_count_report, name="cycle_count_report"),

    # 📌 API - pobieranie szczegółów Itemów
    path("api/get_item_details/", get_item_details, name="get_item_details"),

    # 📌 API - Walidacja kodu scrap
    path("api/check_scrap_code/", check_scrap_code, name="check_scrap_code"),

    # 📌 API - Walidacja lokalizacji
    path("api/check_location/", check_location, name="check_location"),

    path("autocomplete-item/", autocomplete_item, name="autocomplete_item"),
    path("autocomplete-location/", autocomplete_location, name="autocomplete_location"),

    path('notifications/unread/', views.get_unread_notifications, name='get_unread_notifications'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/mark-as-read/<int:notification_id>/', views.mark_as_read, name='mark_as_read'),
     
]


