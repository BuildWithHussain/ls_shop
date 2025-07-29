import frappe


@frappe.whitelist(allow_guest=True)
def get_translations():
	translations = frappe.db.get_all(
		"Translation", fields=["language", "source_text", "translated_text"]
	)

	translation_dict = {}

	for entry in translations:
		lang = entry["language"]
		source_texts = entry["source_text"].split("\n")  # Split source text
		translated_texts = entry["translated_text"].split("\n")  # Split translated text

		if lang not in translation_dict:
			translation_dict[lang] = {}
		for i in range(min(len(source_texts), len(translated_texts))):
			translation_dict[lang][source_texts[i].strip()] = translated_texts[
				i
			].strip()

	return translation_dict
