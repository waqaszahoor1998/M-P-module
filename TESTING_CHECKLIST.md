# M&P COD API Integration - Testing Checklist

## Prerequisites

Before testing, ensure:
- [ ] Odoo server is running
- [ ] M&P module is upgraded (Apps → Muller & Phipps → Upgrade)
- [ ] You have at least one customer with complete shipping address
- [ ] You have at least one product with weight configured
- [ ] "M&P Logistics" delivery carrier exists

---

## Test 1: Configuration (No API Credentials)

**Purpose**: Verify the module works in local mode without API

### Steps:
1. [ ] Go to **Inventory → Configuration → Delivery Methods**
2. [ ] Find or create **"M&P Logistics"** delivery carrier
3. [ ] Set **Delivery Type** to **"M&P Logistics"**
4. [ ] Leave **M&P Username** and **M&P Password** empty
5. [ ] Set **Service Type** to **"Second Day (S)"**
6. [ ] Check **"Auto-create Logistics Operation"**
7. [ ] Save

### Expected Result:
- ✅ Carrier saves successfully
- ✅ "M and P Configuration" tab is visible
- ✅ No errors

---

## Test 2: Create Test Data

**Purpose**: Set up test customer and product

### Steps:
1. [ ] Go to **Sales → Customers**
2. [ ] Create new customer:
   - **Name**: "Test Customer"
   - **Email**: test@example.com
   - **Phone**: 03331234567
   - **Street**: "123 Test Street"
   - **City**: "Karachi"
   - **Country**: Pakistan
3. [ ] Go to **Inventory → Products**
4. [ ] Create new product:
   - **Name**: "Test Product"
   - **Type**: Storable Product
   - **Weight**: 1.5 kg
   - **Sale Price**: 1000

### Expected Result:
- ✅ Customer created with complete address
- ✅ Product created with weight

---

## Test 3: Sales Order with Local Mode (No API)

**Purpose**: Test workflow without API credentials

### Steps:
1. [ ] Go to **Sales → Orders → Quotations**
2. [ ] Create new quotation:
   - **Customer**: Test Customer
   - **Add Product**: Test Product (Qty: 2)
   - **Delivery Method**: M&P Logistics
3. [ ] Click **Confirm** (order becomes "Sale Order")
4. [ ] Go to **Inventory → Transfers**
5. [ ] Find the delivery order for your sale order
6. [ ] Click **Validate** (or **Check Availability** then **Validate**)

### Expected Results:
- ✅ Delivery order validates successfully
- ✅ Logistics Operation is created automatically
- ✅ Local tracking number is generated (format: `MP-TRK-YYYYMMDD-XXXXXX`)
- ✅ Message on delivery order says: "M&P Logistics Operation Created (Local Mode)"
- ✅ Warning mentions: "M&P API credentials not configured"
- ✅ Tracking number appears in delivery order

### Verify:
- [ ] Open **M&P → Logistics Operations**
- [ ] Find the operation linked to your delivery
- [ ] Check tracking number matches delivery order
- [ ] Check operation state is "In Transit"

---

## Test 4: Configure API Credentials (If Available)

**Purpose**: Set up API integration

### Steps:
1. [ ] Go to **Inventory → Configuration → Delivery Methods**
2. [ ] Open **"M&P Logistics"** carrier
3. [ ] Go to **"M and P Configuration"** tab
4. [ ] Enter **M&P Username** (provided by M&P)
5. [ ] Enter **M&P Password** (provided by M&P)
6. [ ] **API URL**: Leave empty (uses default) OR enter custom URL
7. [ ] Set **Service Type**: "Overnight (O)" or "Second Day (S)"
8. [ ] Save

### Expected Result:
- ✅ Credentials saved successfully
- ✅ No validation errors

---

## Test 5: Sales Order with API Integration

**Purpose**: Test full API integration

### Steps:
1. [ ] Create new **Sales Order**:
   - **Customer**: Test Customer (with complete address)
   - **Product**: Test Product (Qty: 1, Weight: 1.5 kg)
   - **Delivery Method**: M&P Logistics
2. [ ] **Confirm** the order
3. [ ] Go to **Inventory → Transfers**
4. [ ] Open the delivery order
5. [ ] Click **Validate**

### Expected Results (With API):
- ✅ Delivery order validates successfully
- ✅ Logistics Operation is created
- ✅ **M&P Order Reference** is received (format: numbers like "544794010000038")
- ✅ Message says: "M&P Shipment Booked Successfully"
- ✅ M&P Order Reference appears in message
- ✅ Tracking number = M&P Order Reference
- ✅ No warning about local mode

### Verify:
- [ ] Open **M&P → Logistics Operations**
- [ ] Check **M&P Order Reference** field is filled
- [ ] Check **Tracking Number** matches M&P reference
- [ ] Check operation state is "In Transit"

### If API Fails:
- ✅ Error message is posted to delivery order
- ✅ Local tracking number is generated as fallback
- ✅ System continues to work

---

## Test 6: View Tracking Information

**Purpose**: Verify tracking links work

### Steps:
1. [ ] Open delivery order with tracking number
2. [ ] Click on **Tracking Number** link (if available)
3. [ ] Or check **Tracking URL** in logistics operation

### Expected Results:
- ✅ Tracking link is clickable
- ✅ URL format: `http://mnpcourier.com/track/{tracking_number}`
- ✅ (If API configured) Uses M&P order reference
- ✅ (If no API) Uses local tracking number

---

## Test 7: Cancel Shipment (With API)

**Purpose**: Test void consignment API

### Steps:
1. [ ] Open delivery order that was booked with M&P API
2. [ ] Click **Cancel** (or set to "Cancelled")
3. [ ] Confirm cancellation

### Expected Results (With API):
- ✅ Void consignment API is called
- ✅ Message says: "M&P Shipment Cancelled"
- ✅ M&P Order Reference is shown in message
- ✅ Logistics operation state changes to "Cancelled"

### Expected Results (No API):
- ✅ Logistics operation is cancelled locally
- ✅ Message confirms cancellation

---

## Test 8: Multiple Products Order

**Purpose**: Test with multiple products and weight calculation

### Steps:
1. [ ] Create sales order with:
   - Product 1: Weight 2.0 kg, Qty 1
   - Product 2: Weight 0.5 kg, Qty 3
   - **Total Weight**: 2.0 + (0.5 × 3) = 3.5 kg
2. [ ] Confirm and validate delivery

### Expected Results:
- ✅ Weight is calculated correctly (3.5 kg)
- ✅ Pieces = 4 (1 + 3)
- ✅ Product details include all products
- ✅ API receives correct weight and pieces

---

## Test 9: Website Checkout (E-commerce)

**Purpose**: Test delivery method appears on website

### Steps:
1. [ ] Go to **Website → Configuration → Settings**
2. [ ] Enable **"Delivery Costs"**
3. [ ] Go to **Website → Go to Website**
4. [ ] Add product to cart
5. [ ] Go to checkout
6. [ ] Check delivery options

### Expected Results:
- ✅ "M&P Logistics" appears as delivery option
- ✅ Shipping cost is calculated
- ✅ Can select M&P Logistics
- ✅ Order can be placed

---

## Test 10: API Error Handling

**Purpose**: Verify graceful error handling

### Steps:
1. [ ] Configure **invalid** API credentials (wrong username/password)
2. [ ] Create and validate delivery order
3. [ ] Check error messages

### Expected Results:
- ✅ Error message is posted to delivery order
- ✅ Error mentions API failure
- ✅ System falls back to local mode
- ✅ Local tracking number is generated
- ✅ No system crash

---

## Test 11: Missing Required Data

**Purpose**: Test validation

### Test Cases:

#### A. Missing Customer Address
1. [ ] Create customer without street address
2. [ ] Create sales order
3. [ ] Try to validate delivery

**Expected**: Error message about missing address

#### B. Missing Product Weight
1. [ ] Create product without weight
2. [ ] Create sales order
3. [ ] Validate delivery

**Expected**: Default weight (0.5 kg) is used

#### C. Missing City
1. [ ] Create customer without city
2. [ ] Create sales order
3. [ ] Validate delivery

**Expected**: Default city ("Karachi") or state name is used

---

## Test 12: Logistics Operation Details

**Purpose**: Verify all data is stored correctly

### Steps:
1. [ ] Open **M&P → Logistics Operations**
2. [ ] Find operation from test order
3. [ ] Check all fields

### Expected Results:
- ✅ **Operation Reference**: Auto-generated
- ✅ **Operation Type**: "Shipment"
- ✅ **Picking**: Linked to delivery order
- ✅ **Sale Order**: Linked to sales order
- ✅ **Carrier**: M&P Logistics
- ✅ **Tracking Number**: M&P reference (if API) or local (if no API)
- ✅ **M&P Order Reference**: Filled if API was used
- ✅ **State**: "In Transit"
- ✅ **Operation Lines**: Products from order

---

## Quick Test Summary

### Minimum Test (5 minutes):
1. ✅ Configure carrier (no API)
2. ✅ Create sales order
3. ✅ Validate delivery
4. ✅ Check tracking number generated

### Full Test (15 minutes):
1. ✅ All minimum tests
2. ✅ Configure API credentials
3. ✅ Test with API
4. ✅ Verify M&P order reference
5. ✅ Test cancellation

### Complete Test (30 minutes):
1. ✅ All full tests
2. ✅ Test multiple products
3. ✅ Test website checkout
4. ✅ Test error handling
5. ✅ Verify all logistics operation fields

---

## Common Issues & Solutions

### Issue: "M&P API credentials are required"
**Solution**: Configure username and password in delivery carrier

### Issue: "Picking must be linked to a sales order"
**Solution**: Ensure delivery order was created from a sales order

### Issue: Delivery method not appearing on website
**Solution**: 
- Check carrier is active
- Check "Availability" tab settings
- Enable "Delivery Costs" in website settings

### Issue: No tracking number generated
**Solution**: 
- Check "Auto-create Logistics Operation" is enabled
- Check delivery order is validated
- Check Odoo logs for errors

### Issue: API call fails
**Solution**:
- Verify username/password are correct
- Check API URL is accessible
- Check Odoo logs for detailed error
- Verify customer has complete address

---

## Success Criteria

✅ **Module works in local mode** (no API needed)
✅ **API integration works** (if credentials provided)
✅ **Tracking numbers are generated** (local or from API)
✅ **Logistics operations are created** automatically
✅ **Error handling works** gracefully
✅ **Delivery method appears** on website
✅ **All data is stored** correctly in logistics operations

---

## Next Steps After Testing

1. **If all tests pass**: Module is ready for use
2. **If API tests fail**: 
   - Verify credentials with M&P
   - Check API URL is correct
   - Review error logs
3. **If local mode works but API doesn't**: 
   - Module still functional
   - Can use local mode until API is fixed
   - Contact M&P support for API issues

---

## Need Help?

- Check **M_P_COD_API_INTEGRATION.md** for detailed API documentation
- Check **Odoo logs**: Settings → Technical → Logging
- Review error messages in delivery order chatter
- Check logistics operation notes


