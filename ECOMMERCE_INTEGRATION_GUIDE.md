# M&P Module - E-Commerce Website Integration Guide

## 🛒 How M&P Integration Works in an Odoo E-Commerce Website

### Scenario: Clothing Website on Odoo

Imagine you have:
- **Website**: `www.yourclothingstore.com` (built on Odoo)
- **Products**: T-shirts, Jeans, Shoes, etc.
- **Checkout**: Standard Odoo checkout with address form
- **Delivery**: M&P Logistics integration

---

## 📱 Complete Customer Journey

### Step 1: Customer Browsing Website

```
Customer visits: www.yourclothingstore.com
├── Views products (T-shirts, Jeans, etc.)
├── Adds items to cart
└── Clicks "Checkout"
```

**What Customer Sees:**
- Product catalog
- Shopping cart
- "Proceed to Checkout" button

**What Happens Behind the Scenes:**
- Odoo's `website_sale` module handles the frontend
- Products are stored in Odoo's product catalog
- Cart is managed by Odoo's e-commerce system

---

### Step 2: Checkout Process

```
Customer fills checkout form:
├── Personal Information
│   ├── Name: "John Doe"
│   ├── Email: "john@example.com"
│   └── Phone: "+1-555-0123"
├── Shipping Address
│   ├── Street: "123 Main Street"
│   ├── City: "New York"
│   ├── ZIP: "10001"
│   ├── State: "New York"
│   └── Country: "United States"
└── Delivery Method Selection
    └── [Customer sees delivery options]
```

**What Customer Sees on Website:**

```
┌─────────────────────────────────────┐
│  CHECKOUT - DELIVERY METHOD        │
├─────────────────────────────────────┤
│                                     │
│  Select a delivery method:         │
│                                     │
│  ○ Standard Shipping               │
│     $15.00 - 5-7 business days     │
│                                     │
│  ○ M&P Logistics                   │
│     $25.00 - 2-3 business days      │
│     ✓ Track your package           │
│                                     │
│  ○ Express Delivery                │
│     $45.00 - Next day delivery     │
│                                     │
│  [Continue to Payment]              │
└─────────────────────────────────────┘
```

**How M&P Appears:**
- M&P Logistics shows as a delivery option
- Price is calculated automatically (via `mp_logistics_rate_shipment`)
- Estimated delivery time is shown
- Tracking feature is highlighted

---

### Step 3: Customer Selects M&P Logistics

```
Customer clicks: "M&P Logistics" option
├── Shipping cost: $25.00 (calculated)
├── Estimated delivery: 2-3 business days
└── Customer proceeds to payment
```

**What Happens Behind the Scenes:**

1. **Rate Calculation:**
   ```python
   # Odoo calls M&P module
   carrier.mp_logistics_rate_shipment(order)
   ├── Calculates weight: 2.5 kg (from products)
   ├── Gets origin: Your warehouse location
   ├── Gets destination: Customer's address
   ├── Calls M&P API (if configured) OR uses fixed price
   └── Returns: $25.00
   ```

2. **Order Created:**
   ```python
   # Odoo creates sale order
   sale_order = {
       'partner_id': customer_record,
       'partner_shipping_id': shipping_address,
       'carrier_id': mp_logistics_carrier,
       'order_line': [
           {'product_id': t_shirt, 'qty': 2},
           {'product_id': jeans, 'qty': 1},
       ],
       'amount_delivery': 25.00,
   }
   ```

---

### Step 4: Payment & Order Confirmation

```
Customer completes payment:
├── Payment processed (Stripe, PayPal, etc.)
├── Order confirmed
└── Customer receives confirmation email
```

**What Customer Sees:**

```
┌─────────────────────────────────────┐
│  ORDER CONFIRMATION                │
├─────────────────────────────────────┤
│                                     │
│  Thank you for your order!          │
│                                     │
│  Order Number: SO00123             │
│  Delivery Method: M&P Logistics    │
│  Shipping Cost: $25.00             │
│                                     │
│  Estimated Delivery:               │
│  December 26, 2025                  │
│                                     │
│  [Track Your Order]                 │
│                                     │
└─────────────────────────────────────┘
```

**What Happens Behind the Scenes:**

1. **Sale Order Created:**
   - Order number: SO00123
   - Status: "Quotation" → "Sales Order"
   - Customer record created/updated
   - Delivery method: M&P Logistics

2. **M&P Logistics Operation Created:**
   ```python
   # Automatically triggered
   logistics_operation = {
       'operation_type': 'shipment',
       'sale_order_id': SO00123,
       'state': 'draft',
       'carrier_id': mp_logistics_carrier,
   }
   ```

3. **Delivery Order Created:**
   - Stock picking created automatically
   - Products reserved from inventory
   - Ready for warehouse processing

---

### Step 5: Warehouse Processing

```
Warehouse staff processes order:
├── Picks products from inventory
├── Packs items
├── Validates delivery order
└── M&P tracking number generated
```

**What Happens:**

1. **Staff Validates Delivery:**
   - Goes to: `Inventory → Delivery → SO00123`
   - Clicks "Validate"
   - M&P module automatically:
     - Generates tracking number: `MP-TRK-20251224-000123`
     - Creates shipment in M&P system (if API connected)
     - Updates logistics operation

2. **Tracking Number Generated:**
   ```python
   # M&P module generates tracking
   tracking_number = "MP-TRK-20251224-000123"
   
   # Updates delivery order
   delivery_order.carrier_tracking_ref = tracking_number
   delivery_order.mp_tracking_number = tracking_number
   
   # Updates logistics operation
   logistics_operation.tracking_number = tracking_number
   logistics_operation.state = "in_transit"
   ```

---

### Step 6: Customer Receives Tracking Information

```
Customer gets email notification:
├── Order shipped email
├── Tracking number: MP-TRK-20251224-000123
└── Link to track package
```

**What Customer Sees:**

```
┌─────────────────────────────────────┐
│  YOUR ORDER HAS SHIPPED!            │
├─────────────────────────────────────┤
│                                     │
│  Order: SO00123                     │
│                                     │
│  Your order has been shipped via    │
│  M&P Logistics                      │
│                                     │
│  Tracking Number:                   │
│  MP-TRK-20251224-000123             │
│                                     │
│  [Track Your Package]               │
│  (Opens M&P tracking page)          │
│                                     │
│  Estimated Delivery:                │
│  December 26, 2025                   │
│                                     │
└─────────────────────────────────────┘
```

**Tracking Link:**
- Customer clicks "Track Your Package"
- Opens: `https://track.mullerphipps.com/MP-TRK-20251224-000123`
- Shows real-time shipment status

---

### Step 7: Real-Time Tracking Updates

```
M&P System updates shipment status:
├── "In Transit" → Customer sees update
├── "Out for Delivery" → Customer notified
└── "Delivered" → Order complete
```

**What Customer Sees on Tracking Page:**

```
┌─────────────────────────────────────┐
│  TRACK YOUR PACKAGE                 │
├─────────────────────────────────────┤
│                                     │
│  Tracking: MP-TRK-20251224-000123   │
│                                     │
│  Status: In Transit                 │
│                                     │
│  Timeline:                          │
│  ✓ Dec 24, 5:00 PM - Shipped       │
│  ✓ Dec 25, 2:00 PM - In Transit    │
│  ○ Dec 26, 9:00 AM - Out for Del.   │
│  ○ Dec 26, 3:00 PM - Delivered     │
│                                     │
│  Current Location:                  │
│  New York Distribution Center       │
│                                     │
└─────────────────────────────────────┘
```

**How Updates Work:**

1. **M&P System Updates:**
   - Shipment moves through M&P network
   - Status changes: "Shipped" → "In Transit" → "Out for Delivery"

2. **Webhook to Odoo:**
   ```json
   POST /api/mp/v1/webhooks/shipment-updated
   {
     "tracking_number": "MP-TRK-20251224-000123",
     "status": "in_transit",
     "location": "New York Distribution Center",
     "estimated_delivery": "2025-12-26"
   }
   ```

3. **Odoo Updates:**
   - Logistics operation status updated
   - Customer can see update in their account
   - Email notification sent (optional)

---

### Step 8: Delivery Confirmation

```
Package delivered:
├── M&P marks as delivered
├── Webhook sent to Odoo
├── Order marked complete
└── Customer can leave review
```

**What Happens:**

1. **M&P Confirms Delivery:**
   - Package delivered to customer
   - Signature captured (if required)
   - Status: "Delivered"

2. **Odoo Updates:**
   ```python
   # Webhook received
   logistics_operation.state = "delivered"
   delivery_order.state = "done"
   sale_order.delivery_status = "delivered"
   ```

3. **Customer Notification:**
   - Email: "Your order has been delivered!"
   - Can leave product review
   - Invoice can be generated

---

## 🔧 Technical Implementation

### 1. Website Configuration

**Enable M&P on Website:**

1. **Go to:** `Website → Configuration → Settings`
2. **Enable:** "Delivery Methods" in e-commerce settings
3. **Configure:** Which carriers to show on website

**Location:** `Website → Configuration → E-Commerce Settings`

```
E-Commerce Settings:
├── Delivery Methods
│   ├── ✓ Show delivery methods on website
│   ├── Available Carriers:
│   │   ├── ✓ Standard Shipping
│   │   ├── ✓ M&P Logistics
│   │   └── ✓ Express Delivery
│   └── Default Carrier: M&P Logistics (optional)
```

---

### 2. Delivery Method Display

**How M&P Appears on Checkout:**

The delivery method is automatically displayed because:
- M&P carrier is **Active** in Odoo
- Carrier is available for customer's address (country/region)
- Carrier meets weight/volume requirements

**Customization Options:**

1. **Display Name:**
   - Default: "M&P Logistics"
   - Can customize: "Fast & Tracked Shipping"

2. **Description:**
   - Add description in carrier settings
   - Shows on checkout: "2-3 business days with tracking"

3. **Price Display:**
   - Shows calculated price
   - Can show: "$25.00" or "Free over $100"

---

### 3. Rate Calculation on Website

**How Price is Calculated:**

```python
# When customer selects address on checkout
# Odoo automatically calls:

carrier.mp_logistics_rate_shipment(order)
├── Gets order weight (from products in cart)
├── Gets origin (your warehouse)
├── Gets destination (customer's address)
├── Calculates price:
│   ├── Base price: $20.00
│   ├── Weight surcharge: +$5.00
│   └── Total: $25.00
└── Returns price to website
```

**Customer Sees:**
- Price updates automatically when address changes
- Real-time calculation
- No page refresh needed (AJAX)

---

### 4. Order Processing Flow

**Complete Flow Diagram:**

```
┌──────────────┐
│   WEBSITE    │ Customer places order
│   (Frontend) │ Selects M&P Logistics
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  SALE ORDER  │ Created in Odoo
│   (Backend)  │ Status: "Quotation"
└──────┬───────┘
       │
       ▼ Payment Confirmed
┌──────────────┐
│  SALE ORDER  │ Status: "Sales Order"
│   (Backend)  │ M&P Logistics Operation Created
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   DELIVERY   │ Stock Picking Created
│    ORDER     │ Products Reserved
└──────┬───────┘
       │
       ▼ Warehouse Validates
┌──────────────┐
│   DELIVERY   │ Status: "Done"
│    ORDER     │ Tracking Number Generated
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  M&P MODULE  │ Sends to M&P API
│              │ Updates Logistics Operation
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  M&P SYSTEM  │ Creates Shipment
│   (External) │ Returns Tracking
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   CUSTOMER   │ Receives Tracking Email
│              │ Can Track Package
└──────────────┘
```

---

## 🎨 Customer-Facing Features

### 1. Checkout Page

**What Customer Sees:**

```html
<!-- Delivery Method Selection -->
<div class="delivery-method">
  <h3>Select Delivery Method</h3>
  
  <div class="carrier-option">
    <input type="radio" name="carrier" value="mp_logistics">
    <label>
      <strong>M&P Logistics</strong>
      <span class="price">$25.00</span>
      <span class="description">
        2-3 business days • Track your package
      </span>
    </label>
  </div>
</div>
```

**Features:**
- Radio button selection
- Price display
- Delivery time estimate
- Tracking badge/icon

---

### 2. Order Confirmation Page

**What Customer Sees After Order:**

```html
<div class="order-confirmation">
  <h2>Thank You for Your Order!</h2>
  
  <div class="order-details">
    <p><strong>Order Number:</strong> SO00123</p>
    <p><strong>Delivery Method:</strong> M&P Logistics</p>
    <p><strong>Shipping Cost:</strong> $25.00</p>
    <p><strong>Estimated Delivery:</strong> December 26, 2025</p>
  </div>
  
  <a href="/my/orders/SO00123" class="btn">
    View Order Details
  </a>
</div>
```

---

### 3. Customer Portal (My Account)

**Order History Page:**

```
┌─────────────────────────────────────┐
│  MY ORDERS                         │
├─────────────────────────────────────┤
│                                     │
│  Order #SO00123                    │
│  Date: Dec 24, 2025                │
│  Status: Shipped                    │
│  Delivery: M&P Logistics           │
│                                     │
│  Tracking: MP-TRK-20251224-000123  │
│  [Track Package]                    │
│                                     │
│  Items:                             │
│  • T-Shirt (x2)                     │
│  • Jeans (x1)                       │
│                                     │
│  [View Details] [Reorder]          │
│                                     │
└─────────────────────────────────────┘
```

**Order Details Page:**

```
┌─────────────────────────────────────┐
│  ORDER DETAILS - SO00123            │
├─────────────────────────────────────┤
│                                     │
│  Shipping Information:              │
│  ──────────────────────             │
│  Carrier: M&P Logistics             │
│  Tracking: MP-TRK-20251224-000123  │
│  Status: In Transit                 │
│                                     │
│  [Track Package]                    │
│                                     │
│  Timeline:                          │
│  ✓ Dec 24 - Order Shipped           │
│  → Dec 25 - In Transit              │
│  ○ Dec 26 - Out for Delivery        │
│                                     │
│  Delivery Address:                  │
│  123 Main Street                    │
│  New York, NY 10001                 │
│                                     │
└─────────────────────────────────────┘
```

---

### 4. Email Notifications

**Order Confirmation Email:**

```
Subject: Order Confirmation - SO00123

Hello John Doe,

Thank you for your order!

Order Details:
- Order Number: SO00123
- Delivery Method: M&P Logistics
- Shipping Cost: $25.00
- Estimated Delivery: December 26, 2025

[View Order] [Track Package]
```

**Shipping Notification Email:**

```
Subject: Your Order Has Shipped! - SO00123

Hello John Doe,

Great news! Your order has been shipped.

Tracking Number: MP-TRK-20251224-000123
Carrier: M&P Logistics

[Track Your Package]

Estimated Delivery: December 26, 2025
```

---

## 🔌 Integration Points

### 1. Website Sale Module

**File:** Odoo's `website_sale` module (built-in)

**How It Works:**
- Odoo's e-commerce automatically shows all active carriers
- M&P appears because it's an active delivery carrier
- No additional code needed!

**Configuration:**
- Carrier must be **Active**
- Carrier must be available for customer's country
- Carrier must meet weight/volume requirements

---

### 2. Checkout Process

**Step-by-Step:**

1. **Customer Enters Address:**
   ```python
   # Odoo validates address
   # Checks available carriers for that address
   available_carriers = carrier.available_carriers(
       partner=shipping_address,
       source=order
   )
   # M&P is included if it matches criteria
   ```

2. **Customer Selects M&P:**
   ```python
   # Order is updated
   order.carrier_id = mp_logistics_carrier
   # Rate is calculated
   rate = carrier.mp_logistics_rate_shipment(order)
   order.amount_delivery = rate['price']
   ```

3. **Customer Completes Payment:**
   ```python
   # Order is confirmed
   order.action_confirm()
   # M&P logistics operation created automatically
   ```

---

### 3. Customer Portal Integration

**My Account Page:**

Odoo automatically shows:
- Order history
- Tracking information (if available)
- Delivery status
- Tracking links

**Customization:**

You can customize the portal view to:
- Highlight M&P tracking
- Show M&P-specific information
- Add M&P branding

---

## 📋 Setup Checklist for E-Commerce

### Pre-Launch

- [ ] **M&P Carrier Configured**
  - Active: ✓
  - API credentials set (if using real API)
  - Service types configured

- [ ] **Website Settings**
  - E-commerce enabled
  - Delivery methods shown on website
  - M&P carrier is active

- [ ] **Products Configured**
  - Products have weight (for shipping calculation)
  - Products are sellable
  - Stock quantities set

- [ ] **Warehouse Setup**
  - Warehouse configured
  - Stock locations set
  - Delivery routes configured

### Testing

- [ ] **Test Checkout Flow**
  - Add products to cart
  - Go to checkout
  - Verify M&P appears as option
  - Select M&P
  - Verify price calculates correctly
  - Complete order

- [ ] **Test Order Processing**
  - Confirm order is created
  - Verify delivery order created
  - Validate delivery order
  - Check tracking number generated

- [ ] **Test Customer Experience**
  - Check order confirmation email
  - Verify tracking link works
  - Test customer portal
  - Verify tracking updates

---

## 🎯 Key Benefits for E-Commerce

### For Customers

1. **Transparent Shipping:**
   - See shipping cost before checkout
   - Know delivery time upfront
   - Track package in real-time

2. **Professional Experience:**
   - Branded M&P delivery
   - Reliable tracking
   - Email notifications

3. **Peace of Mind:**
   - Know where package is
   - Estimated delivery date
   - Delivery confirmation

### For Business

1. **Automated Process:**
   - No manual tracking entry
   - Automatic status updates
   - Reduced customer service calls

2. **Better Customer Service:**
   - Customers can self-serve tracking
   - Real-time updates
   - Professional appearance

3. **Operational Efficiency:**
   - Integrated with warehouse
   - Automatic order processing
   - Complete order visibility

---

## 🚀 Summary

**How It Works:**

1. **Customer visits website** → Browses products
2. **Adds to cart** → Goes to checkout
3. **Selects M&P Logistics** → Price calculated
4. **Completes payment** → Order created
5. **Warehouse processes** → Tracking generated
6. **Customer tracks package** → Real-time updates
7. **Package delivered** → Order complete

**Key Points:**

- ✅ M&P appears automatically on checkout (no extra code)
- ✅ Price calculates in real-time
- ✅ Tracking number generated automatically
- ✅ Customer can track from their account
- ✅ Email notifications sent automatically
- ✅ Works seamlessly with Odoo's e-commerce

**The integration is seamless - customers just see "M&P Logistics" as a delivery option, and everything else happens automatically!** 🎉

