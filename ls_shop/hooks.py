app_name = "ls_shop"
app_title = "Ls Shop"
app_publisher = "hussain@buildwithhussain.com"
app_description = "Ecommerce extension for ERPNext"
app_email = "rahul@buildwithhussain.com"
app_license = "agpl-3.0"

required_apps = ["webshop"]

website_redirects = [
	{"source": "/products", "target": "/en/products"},
	{"source": "/products/(.*)", "target": r"/en/products/\1"},
	{"source": "/", "target": "/en"},
	{"source": "/cart", "target": "/en/cart"},
	{"source": "/cart/checkout", "target": "/en/cart/checkout"},
	{"source": "/account", "target": "en/account/dashboard"},
	{"source": "/account/(.*)", "target": r"/en/account/\1"},
	{"source": "/en/account", "target": "/account/dashboard"},
	{"source": "/ar/account", "target": "/account/dashboard"},
	{"source": "/en-US/(.*)", "target": r"/en/\1"},
	{"source": "/en-GB/(.*)", "target": r"/en/\1"},
]

# website_path_resolver = "ls_shop.utils.resolve_bilingual_path"

website_route_rules = [
	# ------------
	# English Routes
	# ------------
	#
	# -> Landing
	{"from_route": "/en", "to_route": "/products/list.html"},
	# -> Products
	{"from_route": "/en/products", "to_route": "/products/list.html"},
	{"from_route": "/en/products/<path:route>", "to_route": "/products/details.html"},
	# -> Cart / Checkout
	{"from_route": "/en/cart", "to_route": "/cart/cart.html"},
	{"from_route": "/en/cart/checkout", "to_route": "/cart/checkout.html"},
	# -> Account
	{"from_route": "/en/account/dashboard", "to_route": "/account/dashboard.html"},
	{"from_route": "/en/account/profile", "to_route": "/account/profile.html"},
	{"from_route": "/en/account/orders", "to_route": "/account/orders/index.html"},
	{
		"from_route": "/en/account/orders/confirmation",
		"to_route": "/account/orders/confirmation.html",
	},
	{
		"from_route": "/en/account/orders/detail",
		"to_route": "/account/orders/detail.html",
	},
	{"from_route": "/en/account/wishlist", "to_route": "/account/wishlist.html"},
	{"from_route": "/en/account/address", "to_route": "/account/address.html"},
	#
	# ------------
	# Arabic Routes
	# ------------
	#
	# -> Landing
	{"from_route": "/ar", "to_route": "/products/list.html"},
	# -> Products
	{"from_route": "/ar/products", "to_route": "/products/list.html"},
	{"from_route": "/ar/products/<path:route>", "to_route": "/products/details.html"},
	# -> Cart / Checkout
	{"from_route": "/ar/cart", "to_route": "/cart/cart.html"},
	{"from_route": "/ar/cart/checkout", "to_route": "/cart/checkout.html"},
	# -> Account
	{"from_route": "/ar/account/dashboard", "to_route": "/account/dashboard.html"},
	{"from_route": "/ar/account/profile", "to_route": "/account/profile.html"},
	{"from_route": "/ar/account/orders", "to_route": "/account/orders/index.html"},
	{
		"from_route": "/ar/account/orders/confirmation",
		"to_route": "/account/orders/confirmation.html",
	},
	{
		"from_route": "/ar/account/orders/detail",
		"to_route": "/account/orders/detail.html",
	},
	{"from_route": "/ar/account/wishlist", "to_route": "/account/wishlist.html"},
	{"from_route": "/ar/account/address", "to_route": "/account/address.html"},
]

before_request = ["ls_shop.utils.before_request"]

doctype_js = {
	"Item": "public/js/extends/item.js",
	"Sales Order": "public/js/extends/sales_order.js",
}

after_install = "ls_shop.migrate.after_install"


doc_events = {
	"User": {
		"before_insert": "ls_shop.utils.prevent_welcome_email",
	},
	"Payment Entry": {
		"on_submit": [

			"ls_shop.lifestyle_shop_ecommerce.doctype.telr_payment_request.telr_payment_request.refund_payment_for_payment_entry",
		],
	},
	"Sales Order": {
		"on_submit": [
			"ls_shop.jobs.send_order_success_acknowledgement",
			"ls_shop.utils.update_so_status_from_related_doc",
		],
		"on_cancel": [
			"ls_shop.jobs.send_order_cancel_acknowledgement",
			"ls_shop.utils.update_so_status_from_related_doc",
		],
	},
	"Stock Ledger Entry": {
		"after_insert": ["ls_shop.jobs.send_product_back_in_stock_email"]
	},
	"Sales Invoice": {"on_submit": "ls_shop.utils.update_so_status_from_related_doc"},
	"Delivery Note": {"on_submit": "ls_shop.utils.update_so_status_from_related_doc"},
	"Shipment": {"on_submit": "ls_shop.utils.update_so_status_from_related_doc"},
}

jinja = {
	"filters": ["ls_shop.utils.can_return"],
	"methods": ["ls_shop.utils.get_currency_symbol"],
}


ignore_links_on_delete = [
	"Bulk Image Upload Log",
	"Bulk Style Attribute Configurator Creation Log",
]

# Apps
# ------------------


# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ls_shop",
# 		"logo": "/assets/ls_shop/logo.png",
# 		"title": "Lifestyle Shop Ecommerce",
# 		"route": "/ls_shop",
# 		"has_permission": "ls_shop.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ls_shop/css/ls_shop.css"
# app_include_js = "/assets/ls_shop/js/ls_shop.js"

# include js, css files in header of web template
# web_include_css = "/assets/ls_shop/css/ls_shop.css"
# web_include_js = "/assets/ls_shop/js/ls_shop.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ls_shop/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ls_shop/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ls_shop.utils.jinja_methods",
# 	"filters": "ls_shop.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ls_shop.install.before_install"
# after_install = "ls_shop.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ls_shop.uninstall.before_uninstall"
# after_uninstall = "ls_shop.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ls_shop.utils.before_app_install"
# after_app_install = "ls_shop.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ls_shop.utils.before_app_uninstall"
# after_app_uninstall = "ls_shop.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ls_shop.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ls_shop.tasks.all"
# 	],
# 	"daily": [
# 		"ls_shop.tasks.daily"
# 	],
# 	"hourly": [
# 		"ls_shop.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ls_shop.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ls_shop.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ls_shop.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ls_shop.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ls_shop.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------

# after_request = ["ls_shop.utils.after_request"]

# Job Events
# ----------
# before_job = ["ls_shop.utils.before_job"]
# after_job = ["ls_shop.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"ls_shop.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
	{
		"dt": "Email Template",
		"filters": [
			[
				"name",
				"in",
				("Order Confirmation", "Order Cancellation", "Item In Stock"),
			]
		],
	},
]

scheduler_events = {
	"daily": [
		"ls_shop.jobs.delete_notified_oos",
		"ls_shop.jobs.delete_old_draft_quotations",
	],
}
