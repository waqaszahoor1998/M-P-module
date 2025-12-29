# M&P Module - Warehouse Implementation Guide

## 📍 Where Warehouse Functionality is Located

The warehouse part of the M&P module is implemented in **multiple files** that work together:

---

## 🗂️ Main Warehouse Files

### 1. **`models/mp_warehouse.py`** - Core Warehouse Extensions

**Location:** `custom_addons/muller_phipps/models/mp_warehouse.py`

**What It Does:**
- Extends Odoo's `stock.warehouse` model
- Adds M&P-specific warehouse fields
- Handles warehouse codes, types, and cross-warehouse transfers

**Key Components:**

#### A. StockWarehouse Extension
```python
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    # M&P Warehouse Code (auto-generated)
    mp_warehouse_code = fields.Char(string='M&P Warehouse Code')
    
    # Warehouse Type
    warehouse_type = fields.Selection([
        ('distribution', 'Distribution Center'),
        ('regional', 'Regional Warehouse'),
        ('local', 'Local Warehouse'),
        ('cross_dock', 'Cross-Dock Facility'),
    ])
    
    # Cross-warehouse transfer settings
    allow_cross_warehouse_transfer = fields.Boolean()
    preferred_supply_warehouse_ids = fields.Many2many()
    
    # Replenishment rules
    auto_replenishment = fields.Boolean()
    min_stock_level = fields.Float()
    reorder_point = fields.Float()
```

**Where It's Used:**
- Warehouse configuration in Odoo
- Cross-warehouse transfer logic
- Replenishment automation

---

#### B. StockLocation Extension
```python
class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    # M&P Location Code
    mp_location_code = fields.Char(string='M&P Location Code')
    
    # Location Type
    location_type = fields.Selection([
        ('storage', 'Storage'),
        ('picking', 'Picking Zone'),
        ('packing', 'Packing Zone'),
        ('shipping', 'Shipping Zone'),
        ('receiving', 'Receiving Zone'),
        ('quarantine', 'Quarantine'),
        ('repair', 'Repair Area'),
    ])
    
    # Capacity management
    max_capacity = fields.Float()
    current_utilization = fields.Float(compute='_compute_utilization')
```

**Where It's Used:**
- Location management within warehouses
- Capacity tracking
- Zone organization

---

#### C. StockPicking Extension (Delivery Orders)
```python
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # M&P Logistics Operation link
    mp_logistics_operation_id = fields.Many2one('mp.logistics.operation')
    
    # Cross-warehouse transfer detection
    is_cross_warehouse_transfer = fields.Boolean(compute='_compute_cross_warehouse')
    source_warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_warehouses')
    dest_warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_warehouses')
    
    # M&P Tracking
    mp_tracking_number = fields.Char(string='M&P Tracking Number')
    estimated_delivery_date = fields.Datetime()
```

**Where It's Used:**
- Delivery orders (WH/OUT/xxxxx)
- Cross-warehouse transfer detection
- Tracking number storage

---

#### D. StockMove Extension
```python
class StockMove(models.Model):
    _inherit = 'stock.move'
    
    # M&P Operation Type
    mp_operation_type = fields.Selection([
        ('normal', 'Normal'),
        ('replenishment', 'Replenishment'),
        ('transfer', 'Transfer'),
        ('return', 'Return'),
    ])
```

**Where It's Used:**
- Individual product moves
- Operation type classification

---

### 2. **`workflows/logistics_workflow.py`** - Warehouse Workflow Automation

**Location:** `custom_addons/muller_phipps/workflows/logistics_workflow.py`

**What It Does:**
- Automates warehouse operations when orders are confirmed
- Links warehouses to logistics operations
- Handles delivery confirmation

**Key Functions:**

#### A. Order Fulfillment Automation
```python
def automate_order_fulfillment(self, sale_order):
    """Automatically creates logistics operation and links to warehouse"""
    
    # Creates logistics operation
    logistics_op = self.env['mp.logistics.operation'].create({...})
    
    # Links to stock picking (delivery order)
    if sale_order.picking_ids:
        picking = sale_order.picking_ids[0]
        picking.write({
            'mp_logistics_operation_id': logistics_op.id,
        })
        
        # Links warehouses
        logistics_op.write({
            'origin_warehouse_id': picking.location_id.warehouse_id.id,
            'destination_warehouse_id': picking.location_dest_id.warehouse_id.id,
        })
```

**When It Runs:**
- Automatically when sale order is confirmed
- Links warehouse information to logistics operation

---

#### B. Delivery Confirmation
```python
def process_delivery_confirmation(self, picking):
    """Processes delivery confirmation from warehouse"""
    
    logistics_op = picking.mp_logistics_operation_id
    if logistics_op:
        logistics_op.action_deliver()
        
        # Updates delivered quantities
        for move_line in picking.move_line_ids:
            # Updates logistics operation lines
            ...
```

**When It Runs:**
- Automatically when delivery order is validated
- Updates logistics operation status
- Records delivered quantities

---

### 3. **`workflows/supply_chain_workflow.py`** - Supply Chain & Replenishment

**Location:** `custom_addons/muller_phipps/workflows/supply_chain_workflow.py`

**What It Does:**
- Monitors stock levels across warehouses
- Automates replenishment
- Handles cross-warehouse transfers

**Key Functions:**

#### A. Stock Level Monitoring
```python
def check_stock_levels(self, warehouse=None):
    """Checks stock levels in warehouses"""
    
    warehouses = warehouse or self.env['stock.warehouse'].search([])
    
    for wh in warehouses:
        # Get products in warehouse
        products = self.env['product.product'].search([
            ('location_id.warehouse_id', '=', wh.id),
        ])
        
        # Check against reorder point
        if current_qty <= warehouse.reorder_point:
            # Trigger replenishment
            ...
```

**When It Runs:**
- Can be scheduled (cron job)
- Monitors all warehouses
- Triggers replenishment automatically

---

#### B. Cross-Warehouse Transfer
```python
def automate_cross_warehouse_transfer(self, source_warehouse, dest_warehouse, product, quantity):
    """Automates transfer between warehouses"""
    
    # Checks if cross-warehouse transfer is allowed
    if not source_warehouse.allow_cross_warehouse_transfer:
        raise UserError(...)
    
    # Creates stock picking for transfer
    picking = self.env['stock.picking'].create({
        'location_id': source_warehouse.lot_stock_id.id,
        'location_dest_id': dest_warehouse.lot_stock_id.id,
        ...
    })
    
    # Creates logistics operation
    logistics_op = self.env['mp.logistics.operation'].create({
        'operation_type': 'transfer',
        'origin_warehouse_id': source_warehouse.id,
        'destination_warehouse_id': dest_warehouse.id,
        ...
    })
```

**When It Runs:**
- When stock needs to be transferred between warehouses
- Automatically or manually triggered

---

### 4. **`models/mp_logistics.py`** - Logistics Operations with Warehouse Info

**Location:** `custom_addons/muller_phipps/models/mp_logistics.py`

**What It Does:**
- Stores warehouse information in logistics operations
- Links operations to source/destination warehouses

**Key Fields:**
```python
class MPLogisticsOperation(models.Model):
    # Warehouse links
    origin_warehouse_id = fields.Many2one('stock.warehouse', string='Origin Warehouse')
    destination_warehouse_id = fields.Many2one('stock.warehouse', string='Destination Warehouse')
    
    # Location links
    origin_location_id = fields.Many2one('stock.location', string='Origin Location')
    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
```

**Where It's Used:**
- Logistics operations show warehouse information
- Tracks where shipments come from and go to

---

### 5. **`views/picking_views.xml`** - Warehouse UI in Delivery Orders

**Location:** `custom_addons/muller_phipps/views/picking_views.xml`

**What It Does:**
- Shows warehouse information in delivery order forms
- Displays cross-warehouse transfer status

**What You See:**
```xml
<!-- In Delivery Order Form -->
<group string="M and P Logistics Information">
    <field name="is_cross_warehouse_transfer" readonly="True"/>
    <field name="source_warehouse_id" readonly="True"/>
    <field name="dest_warehouse_id" readonly="True"/>
</group>
```

**Where It Appears:**
- Delivery Order form → "Additional Info" tab
- Shows if it's a cross-warehouse transfer
- Shows source and destination warehouses

---

## 🔄 How Warehouse Operations Flow

### Complete Flow:

```
1. SALE ORDER CREATED
   ↓
2. ORDER CONFIRMED
   ↓ (workflows/logistics_workflow.py)
3. DELIVERY ORDER CREATED (Stock Picking)
   ├── Source: Warehouse Stock Location
   ├── Destination: Customer Address
   └── Warehouse: Determined from sale order
   ↓
4. LOGISTICS OPERATION CREATED
   ├── origin_warehouse_id: Set from picking
   ├── destination_warehouse_id: Set from picking
   └── Linked to delivery order
   ↓
5. WAREHOUSE STAFF PROCESSES
   ├── Picks products from warehouse
   ├── Packs items
   └── Validates delivery order
   ↓ (workflows/logistics_workflow.py)
6. DELIVERY CONFIRMED
   ├── Logistics operation updated
   ├── Tracking number generated
   └── Status: "Delivered"
```

---

## 📍 Where to Find Warehouse Features

### In Odoo Interface:

1. **Warehouse Configuration:**
   - Go to: `Inventory → Configuration → Warehouses`
   - Open any warehouse
   - You'll see M&P fields:
     - **M&P Warehouse Code** (auto-generated)
     - **Region**
     - **Warehouse Type**
     - **Allow Cross-Warehouse Transfer**

2. **Delivery Orders (Stock Pickings):**
   - Go to: `Inventory → Delivery`
   - Open any delivery order
   - Click "Additional Info" tab
   - You'll see:
     - **M&P Logistics Operation**
     - **M&P Tracking Number**
     - **Is Cross-Warehouse Transfer**
     - **Source Warehouse**
     - **Destination Warehouse**

3. **Logistics Operations:**
   - Go to: `M&P Integration → Logistics → Operations`
   - Open any operation
   - You'll see:
     - **Origin Warehouse**
     - **Destination Warehouse**
     - **Origin Location**
     - **Destination Location**

---

## 🛠️ Warehouse Features Implemented

### 1. **Multi-Warehouse Management**
- ✅ Multiple warehouses supported
- ✅ Each warehouse has M&P code
- ✅ Warehouse types (Distribution, Regional, Local, Cross-Dock)

### 2. **Cross-Warehouse Transfers**
- ✅ Automatic detection of cross-warehouse transfers
- ✅ Source and destination warehouse tracking
- ✅ Transfer restrictions (allow/deny)

### 3. **Location Management**
- ✅ Location types (Storage, Picking, Packing, Shipping, etc.)
- ✅ Capacity tracking
- ✅ Utilization calculation

### 4. **Automated Workflows**
- ✅ Automatic warehouse linking when order confirmed
- ✅ Automatic logistics operation creation
- ✅ Automatic delivery confirmation processing

### 5. **Stock Monitoring**
- ✅ Stock level checking
- ✅ Reorder point monitoring
- ✅ Automatic replenishment (optional)

---

## 📝 Code Locations Summary

| Feature | File | Class/Function |
|---------|------|----------------|
| Warehouse Extension | `models/mp_warehouse.py` | `StockWarehouse` |
| Location Extension | `models/mp_warehouse.py` | `StockLocation` |
| Picking Extension | `models/mp_warehouse.py` | `StockPicking` |
| Move Extension | `models/mp_warehouse.py` | `StockMove` |
| Order Fulfillment | `workflows/logistics_workflow.py` | `automate_order_fulfillment()` |
| Delivery Confirmation | `workflows/logistics_workflow.py` | `process_delivery_confirmation()` |
| Stock Monitoring | `workflows/supply_chain_workflow.py` | `check_stock_levels()` |
| Cross-Warehouse Transfer | `workflows/supply_chain_workflow.py` | `automate_cross_warehouse_transfer()` |
| Warehouse UI | `views/picking_views.xml` | Delivery order form extensions |
| Logistics Warehouse Links | `models/mp_logistics.py` | `MPLogisticsOperation` fields |

---

## 🎯 Key Warehouse Integration Points

### 1. **When Order is Confirmed:**
```python
# File: workflows/logistics_workflow.py
# Function: automate_order_fulfillment()

# Automatically:
- Gets warehouse from sale order
- Creates delivery order (stock picking)
- Links warehouse to logistics operation
- Sets origin_warehouse_id and destination_warehouse_id
```

### 2. **When Delivery is Validated:**
```python
# File: workflows/logistics_workflow.py
# Function: process_delivery_confirmation()

# Automatically:
- Updates logistics operation status
- Records delivered quantities
- Links warehouse information
```

### 3. **When Cross-Warehouse Transfer:**
```python
# File: models/mp_warehouse.py
# Function: _compute_cross_warehouse()

# Automatically:
- Detects if source ≠ destination warehouse
- Sets is_cross_warehouse_transfer = True
- Shows in delivery order form
```

---

## ✅ Summary

**Warehouse functionality is spread across:**

1. **`models/mp_warehouse.py`** - Core warehouse extensions (80% of warehouse code)
2. **`workflows/logistics_workflow.py`** - Warehouse workflow automation
3. **`workflows/supply_chain_workflow.py`** - Supply chain and replenishment
4. **`views/picking_views.xml`** - Warehouse UI in delivery orders
5. **`models/mp_logistics.py`** - Warehouse links in logistics operations

**Main File:** `models/mp_warehouse.py` contains most of the warehouse logic!

---

**The warehouse part is fully integrated and works automatically with Odoo's standard warehouse operations!** 🏭

