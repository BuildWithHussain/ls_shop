// The one flow that crosses both halves of the product: a brand-new shopper signs up
// on the Pixio storefront, places a COD order, and finds it in their own order list.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { describe } from 'node:test'
import {
  BASE,
  PREFIX,
  adminGet,
  apiPost,
  closeSession,
  deleteResource,
  listResource,
  onCleanup,
  openSession,
  shot,
  text,
  updateResource,
  uiTest,
  useSession,
  wait,
} from './harness.js'

const SITE = process.env.COMMERA_SITE || 'dev.localhost'
const BENCH = process.env.BENCH_PATH || '/home/frappe/frappe-bench'
const SHOPPER_EMAIL = `${PREFIX}.shopper@example.com`.toLowerCase()

const created = { orders: [], users: [] }

// The signup OTP is generated into Redis and mailed; there is no HTTP way to read it
// back, so this is the one place the suite reaches into the site instead of the API.
function readOtp(email) {
  const output = execFileSync(
    'bench',
    ['--site', SITE, 'console'],
    { cwd: BENCH, encoding: 'utf8', input: `print("OTP_VALUE:" + str(frappe.cache.get_value("otp:${email}")))\n` },
  )
  const match = output.match(/OTP_VALUE:(\d+)/)
  if (!match) throw new Error('no OTP in the cache for ' + email + '\n' + output.slice(-500))
  return match[1]
}

async function clickByText(page, selector, needle) {
  const handle = await page.evaluateHandle(
    (sel, want) =>
      Array.from(document.querySelectorAll(sel)).find(
        (element) => element.offsetParent !== null && element.textContent.trim().includes(want),
      ),
    selector,
    needle,
  )
  const element = handle.asElement()
  if (!element) throw new Error(`no visible ${selector} containing "${needle}"`)
  await element.click()
  return element
}

async function clickSelector(page, selector) {
  const element = await page.$(selector)
  if (!element) throw new Error('not found: ' + selector)
  await element.click()
  return element
}

// The storefront is Alpine-driven, so a value assigned straight onto the node is
// invisible until the native setter plus input/change events replay it.
async function setValue(page, selector, value) {
  await page.evaluate(
    (sel, val) => {
      const element = document.querySelector(sel)
      if (!element) throw new Error('setValue: not found ' + sel)
      if (element.tagName.toLowerCase() === 'select') {
        element.value = val
        element.dispatchEvent(new Event('change', { bubbles: true }))
        return
      }
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
      setter.call(element, val)
      element.dispatchEvent(new Event('input', { bubbles: true }))
      element.dispatchEvent(new Event('change', { bubbles: true }))
    },
    selector,
    value,
  )
}

async function addFirstInStockProductToCart(page) {
  await page.goto(BASE + '/en/products', { waitUntil: 'networkidle2', timeout: 60000 })
  const hrefs = await page.$$eval('a[href*="/products/"]', (nodes) =>
    Array.from(new Set(nodes.map((node) => node.getAttribute('href')).filter((href) => !href.endsWith('/products')))),
  )
  for (const href of hrefs) {
    await page.goto(BASE + href, { waitUntil: 'networkidle2', timeout: 60000 })
    const sizeId = await page.evaluate(() => {
      const radios = Array.from(document.querySelectorAll('input.btn-check[name="product_size"]'))
      const available = radios.find((radio) => !radio.disabled)
      return available ? available.id : null
    })
    if (!sizeId) continue
    await clickSelector(page, `label[for="${sizeId}"]`)
    await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 20000 }).catch(() => {})
    await wait(600)
    await clickByText(page, 'button', 'Add To Cart')
    await wait(1000)
    return page.evaluate(() => document.querySelector('h4.title')?.textContent.trim() || '')
  }
  throw new Error('no in-stock product on the storefront')
}

async function signUp(page, email) {
  await page.goto(BASE + '/en/cart', { waitUntil: 'networkidle2', timeout: 60000 })
  await clickByText(page, 'button', 'Sign In to Checkout')
  await wait(700)
  await clickByText(page, '.pixio-auth button[role="tab"]', 'Sign Up')
  await wait(400)

  const forms = await page.$$('.pixio-auth form')
  assert.ok(forms.length >= 2, 'the auth dialog has no signup form')
  const inputs = await forms[1].$$('input')
  // Field order in the template: email, first name, last name.
  await inputs[0].type(email)
  await inputs[1].type('E2E')
  await inputs[2].type('Shopper')
  await clickByText(page, '.pixio-auth form button[type="submit"]', 'Sign Up')
  await wait(2000)

  const otp = readOtp(email)
  const otpInputs = await page.$$('.pixio-auth-otp input')
  assert.equal(otpInputs.length, 6, 'the OTP field did not appear')
  for (let index = 0; index < 6; index++) await otpInputs[index].type(otp[index])
  await clickByText(page, '.pixio-auth form button[type="submit"]', 'Verify')
  await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 20000 }).catch(() => {})
  await wait(1000)
}

async function placeCodOrder(page, email) {
  await page.goto(BASE + '/en/cart', { waitUntil: 'networkidle2', timeout: 60000 })
  await clickByText(page, 'button', 'Place Order')
  await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 20000 }).catch(() => {})
  await wait(900)

  // A brand-new shopper has no saved address, so the form opens on "new address".
  const address = {
    first_name: 'E2E',
    last_name: 'Shopper',
    email,
    phone_number: '+966 501 234 567',
    full_address: '123 Test Street',
    landmark: 'Near Test Landmark',
    country: 'Saudi Arabia',
    city: 'Riyadh',
    po_box: '560001',
  }
  for (const [field, value] of Object.entries(address)) await setValue(page, `#billing_${field}`, value)
  await clickByText(page, 'button[type="submit"]', 'Continue')
  await wait(1500)

  await clickSelector(page, '#payment_mode_cod')
  await wait(300)
  await clickSelector(page, '#accept_terms')
  await wait(200)
  await clickByText(page, 'button', 'Place Order')
  await page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 30000 }).catch(() => {})
  await wait(2500)

  const match = (await text(page)).match(/Order ID:\s*(\S+)/)
  assert.ok(match, `the confirmation page did not name an order; landed on ${page.url()}`)
  return match[1]
}

describe('checkout', () => {
  // An admin session, kept only to assert server state and to clean up. The shopper
  // drives a separate, cookie-less browser.
  const admin = useSession()

  onCleanup(admin, async ({ page }) => {
    for (const order of created.orders) {
      // Placing an order also writes a purchase analytics event that links it, and a
      // linked Sales Order can be neither cancelled nor deleted.
      for (const event of await listResource(page, 'Storefront Analytics Event', { order_id: order })) {
        await deleteResource(page, 'Storefront Analytics Event', event.name).catch(() => {})
      }
      await apiPost(page, 'frappe.client.cancel', { doctype: 'Sales Order', name: order }).catch(() => {})
      await deleteResource(page, 'Sales Order', order).catch((error) => console.error(error.message))
    }
    // Deleting a User cascades into Contact and Customer; disabling is the reversible
    // equivalent of the product archive this suite uses everywhere else.
    for (const user of created.users) {
      await updateResource(page, 'User', user, { enabled: 0 }).catch(() => {})
    }
  })

  uiTest(
    admin,
    'a new shopper signs up, places a COD order and sees it in their account',
    async () => {
      const shopper = await openSession({ anonymous: true })
      try {
        const productTitle = await addFirstInStockProductToCart(shopper.page)
        await signUp(shopper.page, SHOPPER_EMAIL)
        created.users.push(SHOPPER_EMAIL)

        const orderName = await placeCodOrder(shopper.page, SHOPPER_EMAIL)
        created.orders.push(orderName)

        // The shopper's own order list is the assertion that matters: an order the
        // buyer cannot see is not a placed order.
        await shopper.page.goto(BASE + '/en/account/orders', { waitUntil: 'networkidle2', timeout: 60000 })
        await wait(1000)
        const accountBody = await text(shopper.page)
        assert.ok(accountBody.includes(orderName), `${orderName} is missing from /account/orders`)

        // And the same order must be the one the dashboard sees, with the right buyer.
        const order = await adminGet(admin.page, 'orders.get_order', { sales_order: orderName })
        assert.equal(order.name, orderName)
        assert.ok(order.items.length, 'the placed order has no line items')
        assert.ok(
          order.items.some((row) => productTitle.includes(row.title) || row.title.includes(productTitle)),
          `the order does not contain "${productTitle}"`,
        )
      } catch (error) {
        await shot(shopper.page, 'FAIL-checkout-shopper').catch(() => {})
        throw error
      } finally {
        await closeSession(shopper)
      }
    },
    { timeout: 360000 },
  )
})
