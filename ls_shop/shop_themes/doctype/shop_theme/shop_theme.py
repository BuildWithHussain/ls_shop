import os
import re
import shutil
from contextlib import contextmanager

import frappe
from frappe.model.document import Document
from frappe.modules.utils import export_module_json

# frappe.scrub() does not strip path separators, so it is not a sanitiser.
THEME_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")

DEFAULT_THEME_APP = "ls_shop"
DEFAULT_THEME_MODULE = "Shop Themes"

THEME_CONTEXT_CACHE_KEY = "shop_theme_context"
PREVIEW_THEME_PARAM = "preview_theme"


class ShopTheme(Document):
	def validate(self):
		validate_theme_name(self.theme_name)
		self.validate_unique_slug()
		if self.parent_theme:
			self.validate_no_circular_inheritance()

	def validate_unique_slug(self):
		# "Foo Bar" and "Foo-Bar" scrub to the same slug, and on_trash rmtrees by slug: one delete takes both.
		# ponytail: scrubs every theme name in python, revisit if a site ever ships enough
		# themes for this to matter
		slug = frappe.scrub(self.theme_name)
		# "" rather than self.name: a new doc has no name yet, and `!= NULL` matches no rows.
		filters = {"name": ("!=", self.name or "")}
		for theme_name in frappe.get_all("Shop Theme", filters=filters, pluck="theme_name"):
			if frappe.scrub(theme_name) == slug:
				frappe.throw(frappe._("Theme {0} already uses the folder name {1}").format(theme_name, slug))

	def after_insert(self):
		# A read-only apps volume would otherwise break the insert itself.
		if frappe.conf.developer_mode:
			scaffold_theme(self.theme_name, self.module)

	@frappe.whitelist(methods=["POST"])
	def scaffold_theme_settings(self):
		self.check_permission("write")

		settings_doctype = f"{self.theme_name} Settings"
		if frappe.db.exists("DocType", settings_doctype):
			frappe.throw(frappe._("DocType {0} already exists").format(settings_doctype))

		create_theme_settings_doctype(settings_doctype, self.module)
		self.db_set("theme_settings", settings_doctype)
		return settings_doctype

	def after_rename(self, old_name, new_name, merge=False):
		validate_theme_name(old_name)
		validate_theme_name(new_name)

		old_slug = frappe.scrub(old_name)
		new_slug = frappe.scrub(new_name)

		if old_slug != new_slug:
			app_path = frappe.get_app_path(get_app_for_module(self.module))
			for base_dir in (
				os.path.join(app_path, "themes"),
				os.path.join(app_path, "public", "themes"),
			):
				old_path = get_contained_path(base_dir, old_slug)
				new_path = get_contained_path(base_dir, new_slug)
				if os.path.isdir(old_path):
					os.rename(old_path, new_path)

			if self.module and frappe.conf.developer_mode:
				rename_theme_export_dir(self.module, old_slug, new_slug)

		self.db_set("theme_name", new_name)

		if frappe.conf.developer_mode and self.is_standard and self.module:
			self.theme_name = new_name
			export_module_json(self, is_standard=True, module=self.module)

	def on_update(self):
		if not frappe.conf.developer_mode:
			return

		doc_before = self.get_doc_before_save()
		if doc_before and not any(self.get(field) != doc_before.get(field) for field in EXPORTED_FIELDS):
			return

		export_module_json(self, is_standard=bool(self.is_standard), module=self.module)

	def on_change(self):
		clear_theme_cache()

	def on_trash(self):
		# A standard theme's folders are app source; deleting the record must never rmtree them.
		if not frappe.conf.developer_mode or self.is_standard:
			return

		validate_theme_name(self.name)
		paths = [get_theme_dir(self.name), get_theme_public_dir(self.name)]
		if self.module:
			paths.append(get_theme_export_dir(self.module, frappe.scrub(self.name)))
		for path in paths:
			if os.path.isdir(path):
				shutil.rmtree(path)

	def validate_no_circular_inheritance(self):
		visited = {self.name}
		current = self.parent_theme
		while current:
			if current in visited:
				frappe.throw(frappe._("Circular theme inheritance detected: {0}").format(current))
			visited.add(current)
			current = frappe.db.get_value("Shop Theme", current, "parent_theme")


EXPORTED_FIELDS = ("theme_name", "parent_theme", "config", "is_standard", "module", "theme_settings")


def validate_theme_name(theme_name):
	if not THEME_NAME_PATTERN.match(theme_name or ""):
		frappe.throw(
			frappe._("Theme name may only contain letters, numbers, spaces, hyphens and underscores")
		)


def is_within_directory(directory, target):
	directory = os.path.realpath(directory)
	target = os.path.realpath(target)
	# The trailing separator rejects the sibling-prefix case: /themes/foo_evil is not inside /themes/foo.
	return target == directory or target.startswith(directory + os.sep)


def get_contained_path(base_dir, *segments):
	path = os.path.join(base_dir, *segments)
	if not is_within_directory(base_dir, path):
		frappe.throw(frappe._("Invalid theme path: {0}").format(path))
	return path


def get_app_for_module(module):
	app = frappe.db.get_value("Module Def", module, "app_name") if module else None
	return app or DEFAULT_THEME_APP


def get_theme_app(theme_name):
	return get_app_for_module(frappe.db.get_value("Shop Theme", theme_name, "module"))


def get_theme_dir(theme_name):
	base_dir = os.path.join(frappe.get_app_path(get_theme_app(theme_name)), "themes")
	return get_contained_path(base_dir, frappe.scrub(theme_name))


def get_theme_public_dir(theme_name):
	base_dir = os.path.join(frappe.get_app_path(get_theme_app(theme_name)), "public", "themes")
	return get_contained_path(base_dir, frappe.scrub(theme_name))


def get_theme_export_dir(module, slug):
	return get_contained_path(frappe.get_module_path(module), "shop_theme", slug)


def rename_theme_export_dir(module, old_slug, new_slug):
	old_export_dir = get_theme_export_dir(module, old_slug)
	new_export_dir = get_theme_export_dir(module, new_slug)
	if os.path.isdir(old_export_dir):
		os.rename(old_export_dir, new_export_dir)
	if not os.path.isdir(new_export_dir):
		return

	for filename in os.listdir(new_export_dir):
		if filename.endswith(".json") and filename != f"{new_slug}.json":
			os.remove(os.path.join(new_export_dir, filename))


def create_theme_settings_doctype(doctype_name, module=None):
	permissions = [
		{
			"role": role,
			"read": 1,
			"write": 1,
			"create": 1,
			"delete": 1,
			"share": 1,
			"print": 1,
			"email": 1,
		}
		for role in ("System Manager", "Website Manager")
	]
	doctype = frappe.new_doc("DocType")
	doctype.update(
		{
			"name": doctype_name,
			"module": module or DEFAULT_THEME_MODULE,
			"custom": 0 if frappe.conf.developer_mode else 1,
			"issingle": 1,
			"fields": [
				{"fieldname": "info_section", "fieldtype": "Section Break", "label": "Theme Settings"}
			],
			"permissions": permissions,
		}
	)
	doctype.insert()
	return doctype


def scaffold_theme(theme_name, module=None):
	app_path = frappe.get_app_path(get_app_for_module(module))
	slug = frappe.scrub(theme_name)
	theme_dir = get_contained_path(os.path.join(app_path, "themes"), slug)

	if os.path.exists(theme_dir):
		return

	for folder in ("pages", "components/includes", "components/macros", "styles"):
		os.makedirs(get_contained_path(theme_dir, folder), exist_ok=True)

	# A real directory, never a symlink to the private tree: .py controllers must stay unreachable over HTTP.
	theme_public_dir = get_contained_path(os.path.join(app_path, "public", "themes"), slug)
	for folder in ("scripts", "images"):
		os.makedirs(get_contained_path(theme_public_dir, folder), exist_ok=True)


def get_theme_names(theme_name):
	"""The inheritance chain child-first, cycle-guarded."""
	names = []
	visited = set()
	current = theme_name
	while current and current not in visited:
		visited.add(current)
		names.append(current)
		current = frappe.db.get_value("Shop Theme", current, "parent_theme")
	return names


def build_theme_context(theme_name):
	if not theme_name:
		return {"theme_name": None, "names": [], "dirs": [], "apps": {}, "settings_doctype": None}

	names = get_theme_names(theme_name)
	apps = {}
	dirs = []
	for name in names:
		app = get_theme_app(name)
		apps[name] = app
		theme_dir = os.path.join(frappe.get_app_path(app), "themes", frappe.scrub(name))
		if os.path.isdir(theme_dir):
			dirs.append(theme_dir)

	return {
		"theme_name": theme_name,
		"names": names,
		"dirs": dirs,
		"apps": apps,
		"settings_doctype": frappe.db.get_value("Shop Theme", theme_name, "theme_settings"),
	}


def get_theme_context(theme_name):
	if not theme_name:
		return build_theme_context(None)
	return frappe.cache.hget(
		THEME_CONTEXT_CACHE_KEY, theme_name, generator=lambda: build_theme_context(theme_name)
	)


def resolve_active_theme():
	try:
		return frappe.get_cached_doc("Shop Theme Settings").active_theme
	except frappe.DoesNotExistError:
		# The doctype does not exist yet during the first migrate that installs it.
		return None


def resolve_theme():
	return requested_preview_theme() or resolve_active_theme()


RENDER_THEME_CONTEXT_LOCAL_KEY = "shop_theme_render_context"


def get_render_theme_context():
	context = getattr(frappe.local, RENDER_THEME_CONTEXT_LOCAL_KEY, None)
	if context is None:
		context = get_theme_context(resolve_theme())
		setattr(frappe.local, RENDER_THEME_CONTEXT_LOCAL_KEY, context)
	return context


def clear_render_theme_context():
	setattr(frappe.local, RENDER_THEME_CONTEXT_LOCAL_KEY, None)


@contextmanager
def render_theme_context(theme_context):
	"""Pin the template helpers to one theme for the duration.

	Previewing a theme that is not live needs this: shop_theme_asset_url() and shop_theme_config()
	read this context, and would otherwise hand the previewed theme's templates the LIVE theme's
	asset URLs and settings Single.
	"""
	previous = getattr(frappe.local, RENDER_THEME_CONTEXT_LOCAL_KEY, None)
	setattr(frappe.local, RENDER_THEME_CONTEXT_LOCAL_KEY, theme_context)
	try:
		yield
	finally:
		setattr(frappe.local, RENDER_THEME_CONTEXT_LOCAL_KEY, previous)


def requested_preview_theme():
	if not frappe.conf.developer_mode:
		return None

	request = getattr(frappe.local, "request", None)
	if not request:
		return None

	theme_name = request.args.get(PREVIEW_THEME_PARAM)
	if not theme_name or not frappe.db.exists("Shop Theme", theme_name):
		return None

	return theme_name


def clear_theme_cache():
	frappe.cache.delete_value(THEME_CONTEXT_CACHE_KEY)
	clear_render_theme_context()
