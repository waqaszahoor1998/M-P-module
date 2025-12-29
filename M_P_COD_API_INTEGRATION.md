# M&P COD API Integration Guide

## Overview

The M&P module now includes full integration with the **M&P COD API** for booking shipments, tracking, and managing deliveries. This integration allows Odoo to communicate directly with M&P's courier system.

## API Documentation

- **Swagger UI**: https://mnpcourier.com/mycodapi/swagger/ui/index#!/
- **Base URL**: `http://mnpcourier.com/mycodapi`

## Configuration

### Step 1: Configure Delivery Carrier

1. Go to **Inventory → Configuration → Delivery Methods**
2. Find or create **"M&P Logistics"** delivery carrier
3. Set **Delivery Type** to **"M&P Logistics"**
4. Go to **"M and P Configuration"** tab

### Step 2: Enter API Credentials

**Required Fields:**
- **M&P Username**: Username provided by M&P
- **M&P Password**: Password for API access

**Optional Fields:**
- **API URL**: Leave empty to use default (`http://mnpcourier.com/mycodapi`)
- **Service Type**: 
  - **Overnight (O)**: Next day delivery
  - **Second Day (S)**: Delivery within 2 days

### Step 3: Enable Auto-create Operations

- Check **"Auto-create Logistics Operation"** to automatically create logistics operations when shipping

## How It Works

### With API Credentials Configured

When you **send shipping** for a delivery order:

1. **Logistics Operation** is created automatically
2. **Shipment is booked** with M&P COD API using:
   - Customer details (name, address, phone, email)
   - Product details (weight, pieces, description)
   - COD amount (total order amount)
   - Service type (Overnight or Second Day)
   - Order reference (Odoo sale order name)

3. **M&P Order Reference** is received and stored
4. **Tracking number** is set to M&P order reference
5. **Success message** is posted to the delivery order

### Without API Credentials (Local Mode)

If API credentials are not configured:

1. **Logistics Operation** is created locally
2. **Local tracking number** is auto-generated (format: `MP-TRK-YYYYMMDD-XXXXXX`)
3. **Shipment is NOT booked** with M&P
4. **Warning message** is posted indicating local mode

## API Endpoints Used

### 1. Book Shipment
- **Endpoint**: `POST /api/Booking/InsertBookingData`
- **When**: Automatically called when sending shipping
- **Returns**: M&P Order Reference ID

### 2. Bulk Booking
- **Endpoint**: `POST /api/Booking/InsertBulkBookingData`
- **When**: Can be used for multiple shipments at once
- **Status**: Available in API service, not yet integrated in UI

### 3. Get Tracking
- **Endpoint**: `POST /api/Tracking/CONSIGNMENT_TRACKING`
- **When**: Can be called to get tracking information
- **Status**: Available in API service, can be integrated for tracking updates

### 4. Void Consignment
- **Endpoint**: `POST /api/Booking/VoidConsignment`
- **When**: Automatically called when canceling shipment
- **Returns**: Confirmation of void

### 5. Get Branches
- **Endpoint**: `POST /api/Branch/Get_Branches`
- **Status**: Available in API service

### 6. Get Locations
- **Endpoint**: `POST /api/Location/Get_Locations`
- **Status**: Available in API service

### 7. Get Cities
- **Endpoint**: `POST /api/Location/Get_Cities`
- **Status**: Available in API service

### 8. QSR Report
- **Endpoint**: `POST /api/Reports/QSR_Report`
- **Status**: Available in API service

### 9. Booking Summary Report
- **Endpoint**: `POST /api/Reports/BookingSummart_Report`
- **Status**: Available in API service

## Data Mapping

### Odoo → M&P API

| M&P API Field | Odoo Source | Notes |
|--------------|-------------|-------|
| `username` | Carrier `mp_api_key` | Username from carrier config |
| `password` | Carrier `mp_api_secret` | Password from carrier config |
| `consigneeName` | `partner_shipping_id.name` | Max 100 chars |
| `consigneeAddress` | `partner_shipping_id.street` | Max 200 chars |
| `consigneeMobNo` | `partner_shipping_id.mobile` or `phone` | Required |
| `consigneeEmail` | `partner_shipping_id.email` | Optional |
| `destinationCityName` | `partner_shipping_id.city` | Required |
| `pieces` | Sum of `move_line_ids.quantity` | Integer |
| `weight` | Sum of `product_id.weight * quantity` | Float (kg) |
| `codAmount` | `sale_order_id.amount_total` | Total order amount |
| `custRefNo` | `sale_order_id.name` | Odoo order reference |
| `productDetails` | Product names from order lines | Max 600 chars |
| `fragile` | Default: "No" | Can be enhanced |
| `service` | Carrier `mp_service_type` | "O" or "S" |
| `remarks` | `logistics_operation.notes` or `sale_order_id.note` | Optional |
| `insuranceValue` | Default: "0" | Can be enhanced |
| `locationID` | Optional | If multi-location |

### M&P API → Odoo

| Odoo Field | M&P API Response | Notes |
|-----------|------------------|-------|
| `mp_order_reference_id` | `orderReferenceId` | Stored in logistics operation |
| `tracking_number` | `orderReferenceId` | Used as tracking number |
| `tracking_url` | Generated from order reference | M&P tracking portal |

## Workflow Example

### Complete Sales Order to Delivery

1. **Create Sales Order**
   - Customer with complete shipping address
   - Products with weights
   - Select "M&P Logistics" as delivery method

2. **Confirm Order**
   - Order moves to "Sale Order" state
   - Delivery order is created automatically

3. **Validate Delivery Order**
   - Click "Validate" on delivery order
   - If API credentials configured:
     - Shipment is booked with M&P
     - M&P Order Reference is received
     - Tracking number is set
   - If no API credentials:
     - Local tracking number is generated
     - Warning message is posted

4. **Track Shipment**
   - Tracking number is visible on delivery order
   - Click tracking link to view M&P tracking (if API configured)

5. **Cancel Shipment** (if needed)
   - Click "Cancel" on delivery order
   - If M&P order reference exists:
     - Void consignment API is called
     - M&P confirms cancellation
   - Logistics operation is cancelled

## Error Handling

### API Errors

If API call fails:
- Error is logged in Odoo logs
- Error message is posted to delivery order
- System falls back to local mode (if possible)
- User is notified via Odoo message

### Common Issues

1. **"M&P API credentials are required"**
   - **Solution**: Configure username and password in delivery carrier

2. **"Authentication failed"**
   - **Solution**: Verify username and password are correct

3. **"Invalid API response format"**
   - **Solution**: Check API URL is correct, verify API is accessible

4. **"Picking must be linked to a sales order"**
   - **Solution**: Ensure delivery order is created from a sales order

## Testing

### Test Without API

1. Leave API credentials empty
2. Create and validate delivery order
3. Verify local tracking number is generated
4. Check warning message about local mode

### Test With API

1. Configure API credentials
2. Create test sales order with:
   - Valid customer with shipping address
   - Products with weights
   - M&P Logistics delivery method
3. Confirm order and validate delivery
4. Check for M&P Order Reference in logistics operation
5. Verify tracking number matches M&P reference

## Advanced Features

### Custom Service Types

The service type mapping can be customized in `mp_cod_api.py`:

```python
service_map = {
    'overnight': 'O',
    'standard': 'S',
}
```

### Fragile Items

Currently defaults to "No". Can be enhanced to:
- Check product attribute for fragile flag
- Check order line notes
- Add custom field to products

### Insurance Value

Currently defaults to "0". Can be enhanced to:
- Calculate based on order value
- Use product insurance settings
- Add custom insurance field

### Location ID

If you have multi-location pickup:
- Store location ID in logistics operation
- Pass to API when booking
- Get locations via `Get_Locations` API

## API Service Methods

All API methods are available in `mp.cod.api.service`:

```python
api_service = self.env['mp.cod.api.service']

# Book shipment
result = api_service.book_shipment(carrier, picking, logistics_operation)

# Get tracking
result = api_service.get_tracking(carrier, consignment_number)

# Void consignment
result = api_service.void_consignment(carrier, consignment_number)

# Get branches
result = api_service.get_branches(carrier)

# Get locations
result = api_service.get_locations(carrier)

# Get cities
result = api_service.get_cities(carrier)

# Get QSR report
result = api_service.get_qsr_report(carrier, month=4, year=2024, location_id='41')

# Get booking summary
result = api_service.get_booking_summary(
    carrier, 
    date_from=datetime(2024, 1, 1),
    date_to=datetime(2024, 1, 31),
    status=2,
    location_id='41'
)
```

## Support

For API issues:
- Check M&P API Swagger documentation
- Verify credentials with M&P support
- Check Odoo logs for detailed error messages

For module issues:
- Check Odoo logs: `Settings → Technical → Logging`
- Verify delivery carrier configuration
- Ensure all required fields are filled

