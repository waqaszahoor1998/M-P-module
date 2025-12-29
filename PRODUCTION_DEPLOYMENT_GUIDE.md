# M&P Module - Production Deployment Guide

## 🚀 Complete Guide to Deploy M&P Integration on Your Odoo Website

---

## 📋 Pre-Deployment Checklist

Before going live, ensure:

- [ ] Module is installed and upgraded
- [ ] M&P API credentials are configured
- [ ] Test connection works
- [ ] Shipping rates are configured correctly
- [ ] Test order placed successfully
- [ ] Delivery booking works
- [ ] Tracking numbers are generated

---

## 🔧 Step 1: Configure M&P Delivery Carrier

### 1.1 Access Delivery Methods

1. **Login to Odoo** as Administrator
2. Go to: **Inventory → Configuration → Delivery Methods**
3. Find **"M and P Logistics"** (or create it if not exists)

### 1.2 Configure Basic Settings

**General Tab:**
- **Name**: `M and P Logistics` (or your preferred name)
- **Delivery Type**: `M&P Logistics` (should be auto-selected)
- **Delivery Product**: Select or create a service product for delivery charges
- **Fixed Price**: Leave empty (we'll use calculated rates) OR set a fixed price if preferred
- **Active**: ✅ **Check this box** (CRITICAL - must be active!)

### 1.3 Configure M&P API Credentials

**M and P Configuration Tab:**
- **M&P Username**: `MYRABANO_43m309` (your actual username)
- **M&P Password**: `M&p12345` (your actual password)
- **M&P Account Number**: `MYRABANO_43m309` (usually same as username)
- **API URL**: `https://mnpcourier.com/mycodapi` (use HTTPS for production)
- **Service Type**: 
  - `Overnight` (O) - Premium, faster delivery
  - `Second Day` (S) - Standard delivery (recommended for most cases)
- **Auto Create Operation**: ✅ Check if you want automatic logistics operations

### 1.4 Configure Shipping Rates

**Shipping Rate Calculation Tab:**
- **Base Fee**: `500` (PKR - adjust based on your M&P contract)
- **Price per kg**: `250` (PKR per kilogram)
- **Min Weight**: `0.5` (minimum weight in kg)
- **Max Weight**: `30` (maximum weight before overweight charges)
- **Overweight Fee per kg**: `500` (PKR per kg over max weight)
- **COD Fee (%)**: `2` (percentage of order value)
- **COD Min Fee**: `50` (minimum COD fee in PKR)

**💡 Tip:** Adjust these values to match your actual M&P contract pricing.

### 1.5 Configure Availability

**Availability Tab:**
- **Country**: Select `Pakistan` (or leave empty for all countries)
- **States**: Leave empty (or select specific states if needed)
- **Weight**: Leave empty (or set min/max if you have weight restrictions)
- **Volume**: Leave empty (unless you have volume restrictions)

**⚠️ Important:** If you set restrictions, make sure they match your actual shipping capabilities!

### 1.6 Test Connection

1. Click **"Test Connection"** button
2. You should see: `Connection Successful. M&P API connection is working!`
3. If it fails, check:
   - Username and password are correct
   - API URL is correct (use HTTPS)
   - Your account has API access enabled

---

## 🌐 Step 2: Configure Website Settings

### 2.1 Enable E-commerce

1. Go to: **Website → Configuration → Settings**
2. Ensure **"E-commerce"** is enabled
3. Go to: **Website → Shop → Configuration**

### 2.2 Configure Shipping

1. Go to: **Website → Configuration → E-commerce Settings**
2. Under **"Shipping"**, ensure:
   - **Shipping Methods** are enabled
   - **M and P Logistics** appears in the list
   - It's **Active** ✅

### 2.3 Configure Payment Methods

1. Go to: **Website → Configuration → Payment Providers**
2. Configure your payment methods:
   - **Cash on Delivery (COD)** - Recommended for M&P
   - **Online Payment** - Stripe, PayPal, etc.
   - **Bank Transfer** - If applicable

**💡 Note:** M&P specializes in COD, so ensure COD payment is configured.

---

## 🛒 Step 3: How It Works on the Website

### 3.1 Customer Experience

**Step 1: Customer Adds Products to Cart**
- Customer browses products
- Adds items to cart
- Proceeds to checkout

**Step 2: Customer Enters Shipping Address**
- Customer enters:
  - Full name
  - Complete address
  - **City** (MUST be a valid Pakistani city from M&P's list)
  - Phone number (will be formatted automatically)
  - Email (optional)

**Step 3: Shipping Method Selection**
- Customer sees available shipping methods
- **"M and P Logistics"** appears with calculated price
- Price is calculated based on:
  - Order weight
  - Destination city
  - COD amount (if COD order)
  - Service type (Overnight vs Second Day)

**Step 4: Order Confirmation**
- Customer confirms order
- Order is created in Odoo
- Delivery order is automatically created

**Step 5: Backend Processing (Automatic)**
- When delivery is validated:
  - M&P API is called automatically
  - Booking is created with M&P
  - Tracking number is received
  - Stored in the delivery order

---

## 📦 Step 4: Backend Workflow (For Staff)

### 4.1 View Orders

1. Go to: **Sales → Orders**
2. Find the customer order
3. Check delivery method is "M and P Logistics"

### 4.2 Process Delivery

1. Go to: **Inventory → Delivery Orders**
2. Find the delivery for the order
3. Click **"Validate"** button
4. **This automatically:**
   - Calls M&P API
   - Creates booking with M&P
   - Gets tracking number
   - Stores it in the delivery order

### 4.3 Check Results

**After validation:**
1. Go to **"Chatter"** tab in delivery order
2. You'll see: `M&P Shipment Booked Successfully`
3. Check **"M and P Logistics Information"** section:
   - M&P Order Reference ID
   - Tracking Number
   - Tracking URL

### 4.4 Track Shipment

1. Click on **"Tracking"** tab in delivery order
2. Or use the tracking URL to view on M&P website
3. Or use the tracking API to get real-time status

---

## ⚙️ Step 5: Production Configuration

### 5.1 Environment Setup

**For Production Server:**
1. **Use HTTPS**: Ensure your Odoo site uses HTTPS
2. **API URL**: Use `https://mnpcourier.com/mycodapi` (not HTTP)
3. **Credentials**: Store securely (never commit to git)
4. **Backup**: Regular backups of database

### 5.2 Security Settings

1. **API Credentials**: 
   - Don't share credentials
   - Use environment variables if possible
   - Restrict access to delivery carrier configuration

2. **User Permissions**:
   - Only authorized users can configure delivery methods
   - Only warehouse staff can validate deliveries

### 5.3 Rate Configuration

**Important:** Update rates to match your M&P contract:

1. Go to: **Inventory → Configuration → Delivery Methods → M and P Logistics**
2. Update **Shipping Rate Calculation** fields:
   - Base Fee: Your actual base fee from M&P
   - Price per kg: Your actual per-kg rate
   - COD Fee: Your actual COD percentage
   - Service multipliers: Adjust if needed

**💡 Tip:** Test with a few orders first, then fine-tune the rates.

---

## 🧪 Step 6: Testing Before Going Live

### 6.1 Test Order Flow

1. **Create Test Order:**
   - Add products to cart
   - Use a test customer with valid Pakistani city
   - Select "M and P Logistics" as delivery method
   - Complete checkout

2. **Validate Delivery:**
   - Go to delivery order
   - Click "Validate"
   - Check if M&P booking is successful

3. **Verify Tracking:**
   - Check tracking number is generated
   - Verify it appears in M&P system

### 6.2 Test Different Scenarios

- ✅ **Standard Order**: Normal weight, standard city
- ✅ **Heavy Order**: Overweight items (test overweight charges)
- ✅ **COD Order**: Test COD fee calculation
- ✅ **Overnight Service**: Test premium pricing
- ✅ **Different Cities**: Test various Pakistani cities

### 6.3 Test Error Handling

- ❌ **Invalid City**: Use a city not in M&P's list
- ❌ **API Failure**: Test what happens if API is down
- ❌ **Invalid Credentials**: Test error messages

---

## 📱 Step 7: Customer-Facing Features

### 7.1 Shipping Calculator

**On Checkout Page:**
- Customer enters address
- System calculates shipping cost automatically
- Shows price before order confirmation
- Updates if customer changes address

### 7.2 Order Tracking

**After Order Placement:**
- Customer receives order confirmation email
- Email includes tracking number (if available)
- Customer can track on website or M&P portal

### 7.3 Order Status Updates

**Automatic Updates:**
- Order status updates when delivery is validated
- Tracking information is available
- Customer can see delivery status

---

## 🔄 Step 8: Ongoing Operations

### 8.1 Daily Workflow

1. **Morning:**
   - Check new orders
   - Prepare shipments
   - Validate deliveries (triggers M&P booking)

2. **During Day:**
   - Monitor API responses
   - Handle any booking errors
   - Update tracking information

3. **Evening:**
   - Review daily bookings
   - Check for any issues
   - Generate reports if needed

### 8.2 Monitoring

**Check Regularly:**
- API connection status
- Booking success rate
- Error logs
- Customer complaints

**Tools:**
- Odoo logs: Check for M&P API errors
- M&P Dashboard: Verify bookings in M&P system
- Odoo Reports: Track delivery performance

---

## 🚨 Troubleshooting

### Issue: "No suitable delivery method could be found"

**Solutions:**
1. Check carrier is **Active** ✅
2. Check **Availability** settings (country, weight, etc.)
3. Verify customer address is valid
4. Check city is in M&P's city list

### Issue: "Invalid Destination" Error

**Solutions:**
1. Customer city must match exactly from M&P's city list
2. Use `Get_Cities_All` API to see valid cities
3. Update customer address with correct city name
4. City names are case-sensitive: "KARACHI" not "Karachi"

### Issue: API Connection Fails

**Solutions:**
1. Check API URL is correct (use HTTPS)
2. Verify username and password
3. Test connection button
4. Check if M&P API is accessible
5. Check Odoo logs for detailed error

### Issue: Shipping Price is Wrong

**Solutions:**
1. Review rate calculation settings
2. Check product weights are configured
3. Verify COD fee calculation
4. Adjust rates to match M&P contract
5. Test with different order scenarios

---

## 📊 Step 9: Reports and Analytics

### 9.1 Available Reports

1. **Sales Orders**: Filter by delivery method "M and P Logistics"
2. **Delivery Orders**: View all M&P deliveries
3. **M&P Reports**: Use QSR Report and Booking Summary Report APIs

### 9.2 Key Metrics to Track

- Total shipments booked
- Booking success rate
- Average shipping cost
- COD vs non-COD orders
- Service type distribution (Overnight vs Second Day)
- City-wise delivery distribution

---

## ✅ Production Checklist

Before going live:

- [ ] Module installed and upgraded
- [ ] M&P carrier configured with real credentials
- [ ] Test connection successful
- [ ] Shipping rates configured correctly
- [ ] Carrier is **Active**
- [ ] Availability settings configured
- [ ] Test order placed and validated
- [ ] M&P booking successful
- [ ] Tracking number received
- [ ] Customer can see shipping option on website
- [ ] Shipping cost calculates correctly
- [ ] Order confirmation works
- [ ] Error handling tested
- [ ] Staff trained on workflow
- [ ] Backup system in place

---

## 🎯 Quick Start Summary

1. **Configure**: Set up M&P carrier with credentials
2. **Test**: Place test order and validate
3. **Go Live**: Enable on website
4. **Monitor**: Watch for issues in first few days
5. **Optimize**: Fine-tune rates based on actual usage

---

## 📞 Support

If you encounter issues:

1. **Check Logs**: Odoo logs show detailed error messages
2. **Test Connection**: Use "Test Connection" button
3. **Verify Credentials**: Double-check username/password
4. **Check API Status**: Verify M&P API is accessible
5. **Review Documentation**: Check this guide and other docs

---

## 🎉 You're Ready!

Once all steps are complete, your M&P integration is ready for production use. Customers can select M&P Logistics as their delivery method, and orders will be automatically booked with M&P when deliveries are validated.

**The module handles everything automatically - you just need to validate deliveries!**

