# Copyright (c) 2025, company@bwhstudios.com and contributors
# For license information, please see license.txt

import xml.etree.ElementTree as ET

import frappe
import requests
from frappe.integrations.utils import (
	create_request_log,
	make_get_request,
	make_post_request,
)
from frappe.model.document import Document

from ls_shop.utils import get_local_lang_url

TELR_BASE_URL = "https://secure.telr.com"
# url = 'https://secure.telr.com/gateway/remote.xml'


class TelrSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		auth_key: DF.Password | None
		authorised_url: DF.Data | None
		cancelled_url: DF.Data | None
		currency: DF.Data | None
		declined_url: DF.Data | None
		remote_auth_key: DF.Password | None
		store_id: DF.Data | None
		test_mode: DF.Check

	# end: auto-generated types
	@frappe.whitelist()
	def get_account_information(self):
		basic_token = self.get_basic_token()
		headers = {
			"accept": "application/json",
			"authorization": f"Basic {basic_token}",
		}
		endpoint = f"{TELR_BASE_URL}/api/v1/accounts"

		try:
			output = make_get_request(endpoint, headers=headers)
			create_telr_request_log(endpoint, headers=headers, output=output)
		except Exception as e:
			create_telr_request_log(endpoint, error=e, headers=headers)
			raise

		return output

	def get_basic_token(self):
		if not self.store_id:
			frappe.throw(frappe._("Please set Store ID for Telr"))

		if not self.auth_key:
			frappe.throw(frappe._("Please set Auth Key for Telr"))

		store_id = self.store_id
		auth_key = self.get_password("auth_key")

		import base64

		credentials = f"{store_id}:{auth_key}"
		return base64.b64encode(credentials.encode()).decode()

	@frappe.whitelist()
	def create_session(
		self,
		amount: float,
		internal_reference_id: str,
		description: str = "Telr Transaction from Frappe Backend",
		currency_code: str | None = None,
		customer_details: dict | None = None,
	):
		endpoint = f"{TELR_BASE_URL}/gateway/order.json"

		payload = {
			"method": "create",
			"store": self.store_id,
			"authkey": self.get_password("auth_key"),
			"framed": 0,
			"order": {
				"cartid": internal_reference_id,
				"test": "1" if self.test_mode else "0",
				"amount": str(amount),
				"currency": currency_code or self.currency_code or "SAR",
				"description": description,
			},
			"return": {
				"authorised": get_local_lang_url(
					f"{self.authorised_url}?payment_mode=telr&payment_id={internal_reference_id}"
				),
				"declined": get_local_lang_url(self.declined_url),
				"cancelled": get_local_lang_url(self.cancelled_url),
			},
			"customer": customer_details or {},
		}

		headers = {"accept": "application/json", "Content-Type": "application/json"}

		output = None
		try:
			output = make_post_request(endpoint, json=payload, headers=headers)

			# these idiots return 200 on error too
			if error := output.get("error"):
				frappe.errprint("Telr Response:")
				frappe.errprint(output)
				raise Exception(
					f'{error.get("message")}: {frappe.bold(error.get("note"))}'
				)

			create_telr_request_log(
				endpoint, data=payload, headers=headers, output=output
			)
		except Exception as e:
			create_telr_request_log(endpoint, error=e, headers=headers)
			raise
		return output

	@frappe.whitelist()
	def get_order_for_check(self, order_ref: str):
		endpoint = f"{TELR_BASE_URL}/gateway/order.json"
		payload = {
			"method": "check",
			"store": self.store_id,
			"authkey": self.get_password("auth_key"),
			"order": {"ref": order_ref},
		}

		headers = {"accept": "application/json", "Content-Type": "application/json"}
		try:
			response = make_post_request(endpoint, json=payload, headers=headers)
			create_telr_request_log(
				endpoint, data=payload, headers=headers, output=response
			)
		except Exception as e:
			create_telr_request_log(endpoint, data=payload, headers=headers, error=e)
			raise

		return response

	@frappe.whitelist()
	def refund_order(self, transaction_ref: str, amount: float):
		store_id = self.store_id
		api_key = self.get_password("remote_auth_key")
		currency = self.currency or "SAR"

		url = f"{TELR_BASE_URL}/gateway/remote.xml"
		xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<remote>
    <store>{store_id}</store>
    <key>{api_key}</key>
    <tran>
        <type>refund</type>
        <class>ecom</class>
        <description>Refund for order on Lifestyle Shop Ecommerce Store.</description>
        <test>{1 if self.test_mode else 0}</test>
        <currency>{currency}</currency>
        <amount>{amount}</amount>
        <ref>{transaction_ref}</ref>
    </tran>
</remote>"""

		headers = {"Content-Type": "application/xml", "Accept": "application/xml"}
		response = requests.post(url, data=xml_data, headers=headers)

		root = ET.fromstring(response.text)
		status = root.find("auth/status").text
		message = root.find("auth/message").text

		if status == "A":
			create_telr_request_log(
				url, data=xml_data, headers=headers, output=response.text
			)
		else:
			create_telr_request_log(
				url, data=xml_data, headers=headers, output=response.text, error=message
			)
			frappe.throw(frappe._(message))

		return response


def create_telr_request_log(url: str, data=None, error=None, headers=None, output=None):
	create_request_log(
		data,
		url=url,
		request_headers=headers,
		is_remote_request=True,
		service_name="Telr",
		reference_doctype="Telr Settings",
		reference_docname="Telr Settings",
		output=output,
		error=error,
		status="Failed" if error else "Completed",
	)
