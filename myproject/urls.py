from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from core import views
from core.views import (
    index_view, upload_plan, upload_status, plan_na_dzis,
    manufacturing_orders_menu, logout_success, register_scrap,
    register_scrap_success, get_items_by_group, get_item_details,
    warehouse_tickets, warehouse_ticket_detail, update_warehouse_status,
    call_warehouse, get_warehouse_ticket_comments, take_warehouse_ticket,
    close_warehouse_ticket, add_warehouse_comment, production_plan_view,
    get_production_plan_data, update_order_status, get_comments,
    add_comment, upload_production_log, production_report_view,
    warehouse_index, cycle_count_requests,
    update_cycle_count_status, cycle_count_view, check_scrap_code,
    check_location, autocomplete_item, autocomplete_location,
    cycle_count_report, inv_request_list, inv_request_create,
    inv_request_detail, inv_request_approve, inv_request_reject,
    main_display_board, edit_production_plan, production_c2,
    production_rm5, production_b2b, production_gaming,
    production_scancoin, production_comestero, daily_panel,
    get_production_report_data,

    index_production, index_leader, index_planner, index_manager,
    call_technician, call_quality, call_engineer, filtered_display_board,
    take_ticket, close_ticket, inv_request_preview, inv_request_submit,
    inv_request_cancel, get_unread_notifications, notifications_list, mark_as_read
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Main Navigation & Auth ---
    path("", index_view, name="index"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", logout_success, name="logout"),
    path("daily-panel/", views.daily_panel, name="daily_panel"),

    # --- User-specific Panels ---
    path("panel/production/", views.index_production, name="index_production"),
    path("panel/leader/", views.index_leader, name="index_leader"),
    path("panel/planner/", views.index_planner, name="index_planner"),
    path("panel/manager/", views.index_manager, name="index_manager"),
    path("warehouse/", warehouse_index, name="warehouse_index"),

    # --- Production & Planning ---
    path('zlecenia-produkcyjne/', manufacturing_orders_menu, name='manufacturing_orders_menu'),
    path('upload-plan/', views.upload_plan, name='upload_plan'),
    path('edit-production-plan/<int:plan_id>/', views.edit_production_plan, name='edit_production_plan'),
    path('upload-status/', upload_status, name='upload_status'),
    path('plan-na-dzis/', plan_na_dzis, name='plan_na_dzis'),
    path('production-plan/', production_plan_view, name='production_plan'),
    path("upload-production-log/", upload_production_log, name="upload_production_log"),
    path("production-report/", production_report_view, name="production_report"),

    # --- Production Lines ---
    path("production/c2/", views.production_c2, name="production_c2"),
    path("production/rm5/", views.production_rm5, name="production_rm5"),
    path("production/b2b/", views.production_b2b, name="production_b2b"),
    path("production/gaming/", views.production_gaming, name="production_gaming"),
    path("production/scancoin/", views.production_scancoin, name="production_scancoin"),
    path("production/comestero/", views.production_comestero, name="production_comestero"),

    # --- Scrap Registration ---
    path("register-scrap/", views.register_scrap, name="register_scrap"),
    path("register-scrap-success/", register_scrap_success, name="register_scrap_success"),

    # --- Support Tickets (Andon) ---
    path("call-technician/", views.call_technician, name="call_technician"),
    path("call-quality/", views.call_quality, name="call_quality"),
    path("call-engineer/", views.call_engineer, name="call_engineer"),
    path("display_board/", views.main_display_board, name="main_display_board"),
    path("display_board/<str:category>/", views.filtered_display_board, name="filtered_display_board"),
    path("take-ticket/<int:ticket_id>/", views.take_ticket, name="take_ticket"),
    path("close-ticket/<int:ticket_id>/", views.close_ticket, name="close_ticket"),

    # --- Warehouse Tickets ---
    path("call-warehouse/", call_warehouse, name="call_warehouse"),
    path("warehouse-tickets/", warehouse_tickets, name="warehouse_tickets"),
    path("warehouse-ticket/<int:ticket_id>/", warehouse_ticket_detail, name="warehouse_ticket_detail"),
    path("warehouse/take-ticket/<int:ticket_id>/", take_warehouse_ticket, name="take_warehouse_ticket"),
    path("warehouse/close-ticket/<int:ticket_id>/", close_warehouse_ticket, name="close_warehouse_ticket"),
    path("add-warehouse-comment/<int:ticket_id>/", add_warehouse_comment, name="add_warehouse_comment"),
    path("update-warehouse-status/<int:ticket_id>/<str:status>/", update_warehouse_status, name="update_warehouse_status"),

    # --- Inventory Requests ---
    path('inv-requests/', views.inv_request_list, name='inv_request_list'),
    path('inv-requests/new/', views.inv_request_create, name='inv_request_create'),
    path('inv-requests/preview/', views.inv_request_preview, name='inv_request_preview'),
    path('inv-requests/submit/', views.inv_request_submit, name='inv_request_submit'),
    path('inv-requests/<int:req_id>/', views.inv_request_detail, name='inv_request_detail'),
    path('inv-requests/<int:req_id>/approve/', views.inv_request_approve, name='inv_request_approve'),
    path('inv-requests/<int:req_id>/reject/', views.inv_request_reject, name='inv_request_reject'),
    path('inv-requests/<int:req_id>/cancel/', views.inv_request_cancel, name='inv_request_cancel'),

    # --- Cycle Count ---
    path("cycle-count/", cycle_count_view, name="cycle_count_view"),
    path("cycle-count/new/", cycle_count_requests, name="cycle_count_requests"),
    path("cycle-count/update-status/<int:request_id>/<str:status>/", update_cycle_count_status, name="update_cycle_count_status"),
    path("cycle-count/report/", cycle_count_report, name="cycle_count_report"),

    # --- Notifications ---
    path('notifications/unread/', views.get_unread_notifications, name='get_unread_notifications'),
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/mark-as-read/<int:notification_id>/', views.mark_as_read, name='mark_as_read'),

    # --- API / AJAX Endpoints ---
    path("api/get-items-by-group/", get_items_by_group, name="get_items_by_group"),
    path("api/get-item-details/", get_item_details, name="get_item_details"),
    path("api/get-warehouse-comments/<int:ticket_id>/", get_warehouse_ticket_comments, name="get_warehouse_ticket_comments"),
    path("api/production-plan-data/", get_production_plan_data, name="production_plan_data"),
    path("api/update-order-status/<int:plan_id>/", update_order_status, name="update_order_status"),
    path("api/get-comments/<int:plan_id>/", get_comments, name="get_comments"),
    path("api/add-comment/<int:plan_id>/", add_comment, name="add_comment"),
    path("api/production-report-data/", get_production_report_data, name="get_production_report_data"),
    path("api/check-scrap-code/", check_scrap_code, name="check_scrap_code"),
    path("api/check-location/", check_location, name="check_location"),
    path("api/autocomplete-item/", autocomplete_item, name="autocomplete_item"),
    path("api/autocomplete-location/", autocomplete_location, name="autocomplete_location"),
]