# Sales App - Complete Testing Guide

## 🎯 Test the Complete M&P Workflow from Sales App

This guide walks you through testing the **entire flow** from creating a sales order to getting a tracking number.

---

## ✅ Pre-Test Checklist

Before starting, ensure:

- [ ] Module is installed and upgraded
- [ ] M&P carrier is configured with credentials
- [ ] M&P carrier is **Active** ✅
- [ ] Test connection works
- [ ] Products have stock (add via Inventory Adjustments if needed)

---

## 📋 Step-by-Step Testing Flow

### **STEP 1: Create a Customer with Pakistani City**

**⚠️ IMPORTANT:** M&P API only accepts Pakistani cities. Demo customers have US/UAE cities which won't work.

1. **Go to:** `Contacts → Create`

2. **Fill in Customer:**
   - **Name**: `Ahmed Ali`
   - **Is a Company**: Leave unchecked (individual customer)
   - **Customer**: ✅ Check this
   - **Email**: `ahmed.ali@example.com`
   - **Phone**: `03001234567` (11 digits, starting with 0)
   - **Mobile**: `03001234567` (same as phone)

3. **Fill in Address:**
   - **Street**: `House 123, Block A, Gulshan-e-Iqbal`
   - **City**: `KARACHI` ⚠️ **MUST be exact - all caps, from M&P city list**
   - **ZIP**: `75300`
   - **Country**: `Pakistan`
   - **State**: Leave empty (or select if available)

4. **Click "Save"**

**✅ Checkpoint**: Customer created with valid Pakistani city.

---

### **STEP 2: Add Stock to Products**

1. **Go to:** `Inventory → Operations → Inventory Adjustments → Create`

2. **Add Stock:**
   - **Location**: Select your main warehouse stock location
   - **Product**: `Premium Logistics Box - Large`
   - **Counted Quantity**: `10`
   - Click **"Apply"**

3. **Repeat for Other Products:**
   - Add stock to `Standard Logistics Container`: `10` units
   - Add stock to `Express Delivery Package`: `10` units

**✅ Checkpoint**: Products have stock available.

---

### **STEP 3: Create Sales Order**

1. **Go to:** `Sales → Orders → Create`

2. **Fill in Order Header:**
   - **Customer**: Search and select `Ahmed Ali` (the customer you just created)
   - **Date Order**: Today's date (auto-filled)
   - **Warehouse**: Your warehouse (auto-selected)

3. **Add Products:**
   - Click **"Add a product"** button
   - **Product**: Select `Premium Logistics Box - Large`
   - **Quantity**: `2`
   - **Unit Price**: `5000` (PKR) - or leave default
   - Click **"Add a product"** again
   - **Product**: Select `Standard Logistics Container`
   - **Quantity**: `1`
   - **Unit Price**: `3000` (PKR) - or leave default

4. **Add Delivery Method:**
   - Scroll to **"Delivery"** section
   - Click **"Add shipping method"** button
   - In the popup:
     - **Shipping Method**: Select **"M and P Logistics"**
     - Click **"→ Get rate"** button (calculates shipping cost)
     - You should see a price (e.g., PKR 1,250)
     - Click **"Add"** button
   - Shipping method is added to order

5. **Review Order:**
   - **Subtotal**: Should show product totals
   - **Shipping**: Should show calculated M&P shipping cost
   - **Total**: Subtotal + Shipping

6. **Save Order:**
   - Click **"Save"** button
   - Order number appears (e.g., "S00062")
   - Status: **"Quotation"**

**✅ Checkpoint**: Sales order created with M&P delivery method.

---

### **STEP 4: Confirm the Sales Order**

1. **Click "Confirm" Button:**
   - Top of the order form (purple button)
   - Order status changes to: **"Sales Order"**

2. **What Happens Automatically:**
   - ✅ Delivery order is created
   - ✅ Products are reserved from inventory
   - ✅ M&P Logistics Operation is created (if auto-create enabled)

3. **Check Delivery Order:**
   - Go to: `Inventory → Delivery → Delivery Orders`
   - Find the delivery for your order (e.g., "WH/OUT/00079")
   - Status should be: **"Ready"**

**✅ Checkpoint**: Order confirmed, delivery order created.

---

### **STEP 5: Process the Delivery Order**

1. **Open Delivery Order:**
   - Click on the delivery order
   - You'll see:
     - **Products** to deliver
     - **Source Location**: Your warehouse
     - **Destination Location**: Customer address (KARACHI)
     - **Carrier**: M and P Logistics

2. **Check Operations Tab:**
   - Go to **"Operations"** tab
   - Verify:
     - **Demand**: Shows quantity (e.g., 2.00, 1.00)
     - **Quantity**: Should match demand
     - If **Quantity** is 0, set it to match demand

3. **Validate Delivery:**
   - Click **"Validate"** button (top center, purple)
   - **This triggers the M&P API call!**

---

### **STEP 6: Check M&P Booking Results**

After clicking "Validate", check:

1. **Chatter Tab:**
   - Look for message: `M&P Shipment Booked Successfully`
   - Should show:
     - M&P Order Reference: `562683810000002` (example from your test)
     - Message: `Order saved successfully!`

2. **M and P Logistics Information:**
   - Go to **"Extra"** tab (or "Additional Info")
   - Look for **"M and P Logistics Information"** group
   - You should see:
     - **M&P Order Reference ID**: `562683810000002`
     - **Tracking Number**: `562683810000002` (same as order reference)
     - **Tracking URL**: Clickable link

3. **Delivery Order Status:**
   - Status should be: **"Done"**
   - **Carrier Tracking Ref**: Should show tracking number

---

### **STEP 7: Verify in Sales Order**

1. **Go Back to Sales Order:**
   - Return to your sales order
   - Check **"Delivery"** section
   - Should show:
     - Delivery Method: M and P Logistics
     - Tracking: `562683810000002`
     - Status: Delivered

2. **Check Chatter:**
   - Should show delivery confirmation
   - Should show M&P booking confirmation

---

## 🔍 What to Look For (Success Indicators)

### ✅ **Success - Everything Working:**

1. **Sales Order:**
   - ✅ Delivery method: "M and P Logistics"
   - ✅ Shipping cost calculated correctly
   - ✅ Order confirmed successfully

2. **Delivery Order:**
   - ✅ Status: "Done"
   - ✅ Tracking number present
   - ✅ M&P Order Reference ID present

3. **Chatter Messages:**
   - ✅ "M&P Shipment Booked Successfully"
   - ✅ Shows order reference ID
   - ✅ No error messages

4. **M&P Logistics Information:**
   - ✅ Order Reference ID: `562683810000002` (example)
   - ✅ Tracking Number: Same as order reference
   - ✅ Tracking URL: Clickable link

---

## 📊 Expected Results

### **Order Summary:**
```
Sales Order: S00062
Customer: Ahmed Ali
Products: 
  - Premium Logistics Box - Large (x2) = PKR 10,000
  - Standard Logistics Container (x1) = PKR 3,000
Subtotal: PKR 13,000
Shipping (M&P): PKR 1,250 (calculated)
Total: PKR 14,250
```

### **Delivery Order:**
```
Delivery Order: WH/OUT/00079
Status: Done
Carrier: M and P Logistics
Tracking: 562683810000002
M&P Order Reference: 562683810000002
```

### **Chatter Messages:**
```
✓ M&P Shipment Booked Successfully
  M&P Order Reference: 562683810000002
  Message: Order saved successfully!
```

---

## 🧪 Test Different Scenarios

### **Scenario 1: Standard Order**
- Customer: `Ahmed Ali` (KARACHI)
- Products: 1-2 items, normal weight
- Service: Second Day (S)
- **Expected**: Standard shipping cost (Base + Weight)

### **Scenario 2: Heavy Order**
- Customer: Create customer with `LAHORE` city
- Products: Multiple heavy items (>30kg total)
- Service: Second Day (S)
- **Expected**: Base + weight cost + overweight charges

### **Scenario 3: COD Order**
- Customer: Create customer with `ISLAMABAD` city
- Products: Any products
- Payment: Cash on Delivery
- Service: Overnight (O)
- **Expected**: Base + weight + COD fee + overnight premium

---

## 📝 Quick Test Checklist

Use this checklist while testing:

- [ ] Customer created with valid Pakistani city (KARACHI, LAHORE, ISLAMABAD)
- [ ] Products have stock
- [ ] Sales order created
- [ ] Products added with quantities
- [ ] M&P Logistics selected as delivery method
- [ ] Shipping cost calculated
- [ ] Order confirmed
- [ ] Delivery order created
- [ ] Delivery validated
- [ ] M&P booking successful
- [ ] Tracking number received
- [ ] Chatter shows success message
- [ ] M&P Logistics Information section populated

---

## 🎯 Exact Field Values to Use

### **Customer:**
```
Name: Ahmed Ali
Email: ahmed.ali@example.com
Phone: 03001234567
Street: House 123, Block A, Gulshan-e-Iqbal
City: KARACHI (all caps, exact match)
Country: Pakistan
```

### **Products:**
```
Product 1: Premium Logistics Box - Large
  Quantity: 2
  Unit Price: 5000 (PKR)

Product 2: Standard Logistics Container
  Quantity: 1
  Unit Price: 3000 (PKR)
```

### **Delivery Method:**
```
Shipping Method: M and P Logistics
Service Type: Second Day (S)
```

---

## 🚨 Troubleshooting

### Issue: "No suitable delivery method could be found"

**Solutions:**
1. Check M&P carrier is **Active** ✅
2. Check customer city is valid (e.g., "KARACHI")
3. Check availability settings in carrier

### Issue: "Invalid Destination" Error

**Solutions:**
1. Customer city must match exactly from M&P city list
2. Use: `KARACHI`, `LAHORE`, `ISLAMABAD` (all caps)
3. Not: `Karachi`, `karachi`, `Karachi City`

### Issue: "Error sending shipping to M&P"

**Solutions:**
1. Check API credentials are correct
2. Test connection button
3. Check Odoo logs for detailed error
4. Verify customer phone number format (03001234567)

---

## 🎉 Success!

If you see:
- ✅ M&P booking successful message
- ✅ Tracking number in delivery order
- ✅ M&P Order Reference ID
- ✅ No error messages

**Then everything is working perfectly!** 🎉

---

## 🚀 Next Steps

Once testing is successful:

1. **Test on Website**: Place order through website checkout
2. **Test Different Cities**: Try LAHORE, ISLAMABAD, etc.
3. **Test Different Scenarios**: Heavy orders, COD orders, etc.
4. **Go Live**: Start using in production!

**Follow these steps exactly and you'll have a complete working M&P integration!**
