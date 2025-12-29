# Step-by-Step Production Deployment Guide

## 🎯 Complete Step-by-Step Guide to Deploy M&P Module

Follow these steps in order to deploy the M&P module to production.

---

## **STEP 1: Backup Everything** ⚠️

### 1.1 Backup Database
```bash
# Connect to your Odoo database
# Create a backup before making any changes
```

**In Odoo:**
1. Go to **Settings → Database → Backup Database**
2. Or use command line:
   ```bash
   pg_dump -U odoo -d your_database_name > backup_before_mp_module.sql
   ```

### 1.2 Backup Current Module (if upgrading)
- Copy current module folder to backup location
- Or create a git commit if using version control

**✅ Checkpoint:** Backup completed

---

## **STEP 2: Upload Module to Server**

### 2.1 Copy Module Files
- Copy the entire `muller_phipps` folder to your Odoo `custom_addons` directory
- Ensure file permissions are correct:
  ```bash
  chmod -R 755 custom_addons/muller_phipps
  ```

### 2.2 Verify Module Structure
Check that these files exist:
- `__manifest__.py`
- `__init__.py`
- `models/` folder
- `services/` folder
- `views/` folder
- `controllers/` folder

**✅ Checkpoint:** Module files uploaded

---

## **STEP 3: Install/Upgrade Module in Odoo**

### 3.1 Access Apps Menu
1. Login to Odoo as Administrator
2. Go to **Apps** menu (top left)
3. Remove the "Apps" filter (click "Apps" filter and select "All")

### 3.2 Find Module
1. Search for: **"Muller & Phipps"** or **"M&P"**
2. Or look for: **"Muller & Phipps Custom Integration"**

### 3.3 Install Module
1. Click on the module
2. Click **"Install"** button (if new installation)
   - OR click **"Upgrade"** button (if upgrading existing module)
3. Wait for installation to complete

### 3.4 Verify Installation
- Check for any error messages
- Module should show as "Installed"
- Status should be green/active

**✅ Checkpoint:** Module installed successfully

---

## **STEP 4: Configure M&P Delivery Carrier**

### 4.1 Access Delivery Methods
1. Go to: **Inventory → Configuration → Delivery Methods**
2. Look for **"M and P Logistics"** carrier
   - If it exists: Click to open
   - If it doesn't exist: Click **"Create"** button

### 4.2 Configure Basic Settings

**General Tab:**
- **Name**: `M and P Logistics` (or your preferred name)
- **Delivery Type**: Select **"M&P Logistics"** from dropdown
- **Delivery Product**: 
  - Click field → Search for "M and P Logistics Delivery Service"
  - If not found, create a new service product:
    - Name: `M and P Logistics Delivery Service`
    - Type: `Service`
    - Can be Sold: ✅ Check
- **Fixed Price**: Leave empty (we'll use calculated rates)
- **Active**: ✅ **CHECK THIS BOX** (CRITICAL!)

**✅ Checkpoint:** Basic settings configured

---

## **STEP 5: Configure M&P API Credentials**

### 5.1 Open M&P Configuration Tab
1. In the delivery carrier form, click **"M and P Configuration"** tab

### 5.2 Enter API Credentials
Fill in these fields:
- **M&P Username**: `MYRABANO_43m309` (your actual username)
- **M&P Password**: `M&p12345` (your actual password)
- **M&P Account Number**: `MYRABANO_43m309` (usually same as username)
- **API URL**: `https://mnpcourier.com/mycodapi`
  - ⚠️ **Use HTTPS for production!**
- **Service Type**: Select one:
  - `Overnight` (O) - Premium, faster delivery
  - `Second Day` (S) - Standard delivery (recommended)
- **Auto Create Operation**: ✅ Check this box

**✅ Checkpoint:** API credentials entered

---

## **STEP 6: Test API Connection**

### 6.1 Click Test Connection Button
1. In the **"M and P Configuration"** tab
2. Scroll to find **"Test Connection"** button
3. Click the button

### 6.2 Check Results
**Success Message:**
```
Connection Successful. M&P API connection is working!
Successfully retrieved X city(ies) from M&P API.
```

**If Error:**
- Check username and password
- Verify API URL is correct
- Check internet connection
- Verify M&P API is accessible

**✅ Checkpoint:** API connection tested successfully

---

## **STEP 7: Configure Shipping Rates**

### 7.1 Open Shipping Rate Calculation Section
1. In the delivery carrier form
2. Scroll to **"Shipping Rate Calculation"** section

### 7.2 Configure Rate Fields
Enter these values (adjust based on your M&P contract):

- **Base Fee**: `500` (PKR - base shipping cost)
- **Price per kg**: `250` (PKR per kilogram)
- **Min Weight**: `0.5` (minimum weight in kg)
- **Max Weight**: `30` (maximum weight before overweight charges)
- **Overweight Fee per kg**: `500` (PKR per kg over max weight)
- **COD Fee Percent**: `2.0` (percentage of order value for COD)
- **COD Min Fee**: `5.0` (minimum COD fee in PKR)

**Note:** These are example values. Adjust based on your actual M&P contract.

**✅ Checkpoint:** Shipping rates configured

---

## **STEP 8: Configure Availability (Optional)**

### 8.1 Open Availability Tab
1. In the delivery carrier form
2. Click **"Availability"** tab

### 8.2 Set Availability Rules
**For Production:**
- **Countries**: Leave empty (all countries) OR select specific countries
- **States**: Leave empty (all states) OR select specific states
- **Weight**: Leave empty (all weights) OR set min/max
- **Volume**: Leave empty (all volumes) OR set min/max

**Recommendation:** Leave empty for maximum availability, or restrict based on your business needs.

**✅ Checkpoint:** Availability configured (if needed)

---

## **STEP 9: Save and Activate Carrier**

### 9.1 Save Configuration
1. Click **"Save"** button (top left)
2. Verify no error messages appear

### 9.2 Verify Carrier is Active
1. Check that **"Active"** checkbox is checked ✅
2. Carrier should appear in delivery method lists

**✅ Checkpoint:** Carrier saved and active

---

## **STEP 10: Test Complete Workflow**

### 10.1 Create Test Customer
1. Go to: **Contacts → Create**
2. Fill in:
   - **Name**: `Test Customer`
   - **Customer**: ✅ Check
   - **Phone**: `03001234567`
   - **City**: `KARACHI` (must be valid Pakistani city)
   - **Country**: `Pakistan`
   - **Street**: `123 Test Street`
3. Click **"Save"**

### 10.2 Create Test Sales Order
1. Go to: **Sales → Orders → Create**
2. Fill in:
   - **Customer**: Select "Test Customer"
   - **Products**: Add 1-2 products with weight
   - **Delivery Method**: Click "Add shipping method" → Select "M and P Logistics"
   - Click "→ Get rate" to calculate shipping
3. Click **"Save"**

### 10.3 Confirm Order
1. Click **"Confirm"** button
2. Order status should change to "Sales Order"
3. Delivery order should be created automatically

### 10.4 Validate Delivery
1. Go to: **Inventory → Delivery Orders**
2. Find the delivery for your test order
3. Click **"Validate"** button
4. **This triggers M&P API booking!**

### 10.5 Check Results
**In Delivery Order:**
1. Check **"Chatter"** tab:
   - Should see: `M&P Shipment Booked Successfully`
   - Should show M&P Order Reference ID
2. Check **"Extra"** tab → **"M and P Logistics Information"**:
   - M&P Order Reference ID should be populated
   - Tracking Number should be present
   - Tracking URL should be clickable

**✅ Checkpoint:** Complete workflow tested successfully

---

## **STEP 11: Test Tracking**

### 11.1 Click Tracking Link
1. In the delivery order
2. Click on the **"Tracking"** tab or tracking URL
3. Should open Odoo tracking page (not 404 error)

### 11.2 Verify Tracking Works
- Tracking page should load
- Should show tracking information (if API works)
- Or show error message (if API fails, but page should still load)

**✅ Checkpoint:** Tracking works (no 404 errors)

---

## **STEP 12: Enable on Website (If Using E-commerce)**

### 12.1 Check Website Settings
1. Go to: **Website → Configuration → Settings**
2. Ensure **"Delivery Methods"** are enabled

### 12.2 Verify Carrier Appears
1. Go to your Odoo website
2. Add product to cart
3. Go to checkout
4. **"M and P Logistics"** should appear as shipping option
5. Shipping cost should calculate automatically

**✅ Checkpoint:** Website integration works

---

## **STEP 13: Monitor and Verify**

### 13.1 Check Logs
1. Monitor Odoo logs for any errors
2. Look for M&P API calls
3. Check for any failed bookings

### 13.2 Test Real Order
1. Place a real test order
2. Complete the workflow
3. Verify M&P booking is successful
4. Check tracking number is received

### 13.3 Monitor First Few Days
- Watch for any errors
- Verify all bookings are successful
- Check tracking works for customers
- Monitor shipping cost calculations

**✅ Checkpoint:** Monitoring in place

---

## **STEP 14: Go Live! 🚀**

### 14.1 Final Checklist
Before going fully live:
- [ ] Module installed and upgraded
- [ ] API credentials configured correctly
- [ ] Test connection successful
- [ ] Shipping rates configured
- [ ] Carrier is Active
- [ ] Test order completed successfully
- [ ] M&P booking works
- [ ] Tracking works
- [ ] Website integration works (if applicable)
- [ ] Staff trained on workflow
- [ ] Backup created

### 14.2 Start Using
- Begin processing real orders
- Monitor closely for first few days
- Address any issues immediately

**✅ Checkpoint:** Module is live!

---

## 🎉 **SUCCESS!**

If you've completed all steps:
- ✅ Module is installed
- ✅ API is configured
- ✅ Carrier is active
- ✅ Test order works
- ✅ Tracking works
- ✅ Ready for production use

---

## 📋 **Quick Reference**

### **Key Locations:**
- **Delivery Methods**: Inventory → Configuration → Delivery Methods
- **Sales Orders**: Sales → Orders
- **Delivery Orders**: Inventory → Delivery Orders
- **Test Connection**: In carrier settings → M&P Configuration tab

### **Important Fields:**
- **API URL**: `https://mnpcourier.com/mycodapi`
- **Service Type**: `Second Day` (S) or `Overnight` (O)
- **City Format**: Must be exact match (e.g., `KARACHI`, `LAHORE`)

### **Common Issues:**
- **404 Error on Tracking**: Fixed - now uses Odoo controller
- **Invalid Destination**: Use valid Pakistani cities
- **No Delivery Method**: Ensure carrier is Active
- **API Connection Failed**: Check credentials and URL

---

## 🆘 **Need Help?**

If you encounter issues:
1. Check Odoo logs for error messages
2. Use "Test Connection" button
3. Verify API credentials
4. Check city names are correct
5. Review error messages in chatter

**You're all set! Follow these steps and your M&P module will be production-ready!** 🎯

