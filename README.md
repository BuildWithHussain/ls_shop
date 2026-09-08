# LS Shop

A modern, multilingual e-commerce solution built on Frappe Framework that extends ERPNext's capabilities with custom frontend and advanced product management.

<img width="1470" height="800" alt="Screenshot 2025-09-10 at 1 47 38 AM" src="https://github.com/user-attachments/assets/b776c69b-e009-4b9e-99df-06c1e40a8469" />

## RTL

<img width="1470" height="803" alt="Screenshot 2025-09-10 at 1 49 46 AM" src="https://github.com/user-attachments/assets/90180c6e-34d6-454f-b493-e5e984db13ee" />


## 🌟 Features

### 🌍 Multilingual Support
- Built-in internationalization with URL-based language switching (`/en/`, `/ar/`)
- Seamless translation management using Frappe's native translation system
- RTL (Right-to-Left) language support

### 🛍️ Advanced Product Management
- **Style Attribute Configurator (SAC)**: Manage item templates with attributes
- **Style Attribute Variants (SAV)**: Handle product variations efficiently
- Support for complex product hierarchies with multiple attributes and sizes
- Bulk operations for product creation and management

### ⚡ Performance Optimized
- Server-side rendering with Jinja templates
- 6x faster loading times compared to traditional SPA approaches
- Optimized for Core Web Vitals and SEO

### 🎨 Modern Frontend
- Built with Tailwind CSS for responsive design
- Alpine.js for reactive components
- Component library integration (Pines UI, Penguin UI)
- Clean, professional design system

### 💼 E-commerce Capabilities
- Integration with ERPNext's accounting and inventory
- POS integration for offline stores
- Payment gateway integrations (including BNPL services like Tabby)
- Partial refunds and returns management
- Consolidated stock management across channels

## 📄 Pages & Features

The application includes the following key pages and functionalities:

<!-- TODO: Update this section with your actual pages from the demo -->
<!-- Add specific page routes and descriptions based on your www/ directory structure -->
<!-- Example format:
- **Homepage** (`/`): Modern landing page with product highlights
- **Product Catalog** (`/products`): Advanced filtering and search capabilities
- **Product Details** (`/product/[slug]`): Comprehensive product information with variants
- **Shopping Cart** (`/cart`): Seamless cart management
- **Checkout** (`/checkout`): Streamlined checkout process
- **User Account** (`/account`): Order history and profile management
-->

### Frontend Pages
- **Homepage**: Modern landing page with product highlights
- **Product Catalog**: Advanced filtering and search capabilities  
- **Product Details**: Comprehensive product information with variants
- **Shopping Cart**: Seamless cart management
- **Checkout**: Streamlined checkout process
- **User Account**: Order history and profile management
- **Multi-store Support**: Support for multiple physical locations

### Admin/Backend Features
- **Admin Dashboard**: Bulk operations and reporting tools
- **SAC Management**: Style Attribute Configurator administration
- **SAV Management**: Style Attribute Variants handling
- **Bulk Operations**: Mass product creation and image uploads
- **Reporting**: Consolidated inventory and sales reports



## 🔗 Compatibility

This app is compatible with the following versions of Frappe and ERPNext:

| LS Shop branch | Stability   | Frappe branch | ERPNext branch |
| :------------- | :---------- | :------------ | :------------- |
| main           | stable      | v16.x & above | v16.x & above  |
| develop        | maintenance | v15.x         | v15.x          |

## 🚀 Quick Start

### Prerequisites
- Frappe Framework and ERPNext — see [Compatibility](#-compatibility) for the branch to install
- Node.js and npm (for asset compilation)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ls_shop.git
cd ls_shop
```

2. Install the app:
```bash
bench get-app https://github.com/BuildWithHussain/ls_shop
bench install-app ls_shop --site your-site-name
```

3. Build assets:
```bash
bench build --app ls_shop
```

### Key Components
- **WWW Directory**: Server-rendered pages for optimal performance
- **Custom Doctypes**: SAC and SAV for advanced product management
- **Hooks Integration**: URL routing and custom business logic
- **API Layer**: RESTful APIs for frontend interactions



### Project Structure
```
ls_shop/
├── ls_shop/
│   ├── hooks.py              # App configuration and hooks
│   ├── www/                  # Public web pages
│   ├── templates/            # Jinja2 templates
│   ├── public/               # Static assets
│   └── ls_shop/              # App modules
├── requirements.txt          # Python dependencies
└── package.json             # Node.js dependencies
```

## 📊 Bulk Operations

LS Shop provides powerful bulk operation capabilities:

- **Bulk SAC/SAV Creation**: Create multiple product configurations at once
- **Bulk Image Upload**: Upload and associate product images in batches
- **Bulk Publishing**: Publish multiple products to the website simultaneously
- **Consolidated Reporting**: Generate comprehensive reports across all items

## 🔧 Configuration

### Language Setup
Configure supported languages in `hooks.py`:
```python
website_route_rules = [
    {"from_route": "/", "to_route": "/en"},
    {"from_route": "/<path:app_path>", "to_route": "/en/<path:app_path>"},
]
```

### Payment Gateway Integration
The app supports various payment gateways. For Tabby BNPL integration, check out our companion app: [tabby_frappe](https://github.com/cinnamonlabs/tabby_frappe)


## 🏢 About BWH Studios

LS Shop is developed and maintained by BWH Studios, a tech company based in Jagdalpur, Chhattisgarh, specializing in Frappe customizations and consulting.

---

⭐ If you find LS Shop helpful, please consider starring the repository!
