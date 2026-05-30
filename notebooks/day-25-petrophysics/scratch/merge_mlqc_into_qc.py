"""
merge_mlqc_into_qc_lxml.py
===========================
Uses lxml to properly restructure the Qt .ui file.

The plan:
1. Parse mainwindow.ui with lxml (preserves formatting better)
2. Find the centralTabWidget
3. Find tabQualitycontrol and tabMLQC (both children of centralTabWidget)
4. Create a new QTabWidget "tabQCInner" inside tabQualitycontrol
5. Move tabQualitycontrol's layout into a new sub-widget "tabQCStat"
6. Move tabMLQC's layout into tabMLQC (renamed as sub-tab inside tabQCInner)
7. Remove the top-level tabMLQC from centralTabWidget
8. Write back
"""

from lxml import etree
import copy

UI_PATH = "/home/ashraf/Desktop/100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics-Well-log/notebooks/day-25-petrophysics/ui/mainwindow.ui"

# ── Parse ─────────────────────────────────────────────────────────────────
parser = etree.XMLParser(remove_blank_text=False)
tree = etree.parse(UI_PATH, parser)
root = tree.getroot()

def find_widget(parent, name):
    """Find direct or near-direct child widget by name."""
    for w in parent.iter('widget'):
        if w.get('name') == name:
            return w
    return None

# ── Find the key widgets ──────────────────────────────────────────────────
central_tab = find_widget(root, 'centralTabWidget')
qc_tab = find_widget(root, 'tabQualitycontrol')
ml_tab = find_widget(root, 'tabMLQC')

if qc_tab is None:
    raise RuntimeError("tabQualitycontrol not found")
if ml_tab is None:
    raise RuntimeError("tabMLQC not found")

print(f"Found tabQualitycontrol: {qc_tab.tag} name={qc_tab.get('name')}")
print(f"Found tabMLQC: {ml_tab.tag} name={ml_tab.get('name')}")

# ── Find parents ──────────────────────────────────────────────────────────
def find_parent(root, child):
    for parent in root.iter():
        for c in parent:
            if c is child:
                return parent
    return None

qc_parent = find_parent(root, qc_tab)
ml_parent = find_parent(root, ml_tab)

print(f"qc_tab parent: {qc_parent.get('name', qc_parent.tag)}")
print(f"ml_tab parent: {ml_parent.get('name', ml_parent.tag)}")

# ── Deep copy the ML layout content ──────────────────────────────────────
# We'll take the <layout> element from inside tabMLQC
ml_layout = None
for child in ml_tab:
    if child.tag == 'layout':
        ml_layout = copy.deepcopy(child)
        break

if ml_layout is None:
    raise RuntimeError("No layout found in tabMLQC")

# Change the layout name to avoid conflicts
ml_layout.set('name', 'layoutMLQCInner')

# ── Build the new inner QTabWidget structure ──────────────────────────────
# We will replace tabQualitycontrol's content:
#   OLD: <widget name="tabQualitycontrol">
#           <attribute name="title">Quality Control</attribute>
#           <layout ...> ... </layout>
#        </widget>
#
#   NEW: <widget name="tabQualitycontrol">
#           <attribute name="title">Quality Control</attribute>
#           <layout class="QVBoxLayout" name="layoutQCOuter">
#             <property name="spacing">...</property>
#             <property name="leftMargin">...</property>
#             ...
#             <item>
#               <widget class="QTabWidget" name="tabQCInner">
#                 <property name="tabPosition"><enum>QTabWidget::North</enum></property>
#                 <property name="currentIndex"><number>0</number></property>
#                 <widget class="QWidget" name="tabQCStat">
#                   <attribute name="title"><string>Statistical QC</string></attribute>
#                   [original QC layout, renamed]
#                 </widget>
#                 <widget class="QWidget" name="tabMLQC">
#                   <attribute name="title"><string>ML Based QC</string></attribute>
#                   [ML QC layout]
#                 </widget>
#               </widget>
#             </item>
#           </layout>
#        </widget>

# Get and remove the existing QC layout from tabQualitycontrol
qc_layout = None
for child in qc_tab:
    if child.tag == 'layout':
        qc_layout = child
        break

if qc_layout is None:
    raise RuntimeError("No layout found in tabQualitycontrol")

# Rename the existing QC layout to avoid conflict
qc_layout_copy = copy.deepcopy(qc_layout)
qc_layout_copy.set('name', 'layoutQCStatContent')

# Remove the original layout from qc_tab
qc_tab.remove(qc_layout)

# ── Create the tabQCStat sub-widget ──────────────────────────────────────
tab_qc_stat = etree.SubElement(etree.Element('dummy'), 'widget')
tab_qc_stat = etree.Element('widget')
tab_qc_stat.set('class', 'QWidget')
tab_qc_stat.set('name', 'tabQCStat')

attr_stat = etree.SubElement(tab_qc_stat, 'attribute')
attr_stat.set('name', 'title')
stat_str = etree.SubElement(attr_stat, 'string')
stat_str.text = 'Statistical QC'

tab_qc_stat.append(qc_layout_copy)

# ── Create the tabMLQC sub-widget ─────────────────────────────────────────
tab_ml_inner = etree.Element('widget')
tab_ml_inner.set('class', 'QWidget')
tab_ml_inner.set('name', 'tabMLQC')

attr_ml = etree.SubElement(tab_ml_inner, 'attribute')
attr_ml.set('name', 'title')
ml_str = etree.SubElement(attr_ml, 'string')
ml_str.text = 'ML Based QC'

tab_ml_inner.append(ml_layout)

# ── Create the inner QTabWidget ───────────────────────────────────────────
tab_qc_inner = etree.Element('widget')
tab_qc_inner.set('class', 'QTabWidget')
tab_qc_inner.set('name', 'tabQCInner')

# Properties
prop_tabpos = etree.SubElement(tab_qc_inner, 'property')
prop_tabpos.set('name', 'tabPosition')
enum_tabpos = etree.SubElement(prop_tabpos, 'enum')
enum_tabpos.text = 'QTabWidget::North'

prop_curidx = etree.SubElement(tab_qc_inner, 'property')
prop_curidx.set('name', 'currentIndex')
num_curidx = etree.SubElement(prop_curidx, 'number')
num_curidx.text = '0'

tab_qc_inner.append(tab_qc_stat)
tab_qc_inner.append(tab_ml_inner)

# ── Create the outer layout wrapping tabQCInner ───────────────────────────
outer_layout = etree.Element('layout')
outer_layout.set('class', 'QVBoxLayout')
outer_layout.set('name', 'layoutQCOuter')

def make_prop_number(name, value):
    p = etree.Element('property')
    p.set('name', name)
    n = etree.SubElement(p, 'number')
    n.text = str(value)
    return p

outer_layout.append(make_prop_number('spacing', 0))
outer_layout.append(make_prop_number('leftMargin', 0))
outer_layout.append(make_prop_number('topMargin', 0))
outer_layout.append(make_prop_number('rightMargin', 0))
outer_layout.append(make_prop_number('bottomMargin', 0))

item = etree.SubElement(outer_layout, 'item')
item.append(tab_qc_inner)

# ── Attach the new outer layout to tabQualitycontrol ─────────────────────
qc_tab.append(outer_layout)

# ── Remove the top-level tabMLQC from its parent ─────────────────────────
# Find the <item> wrapper around tabMLQC and remove it
def remove_widget_from_parent(root, widget_name):
    """Remove the widget (and its wrapping <item> if any) from its parent."""
    for parent in root.iter():
        for child in list(parent):
            if child.tag == 'widget' and child.get('name') == widget_name:
                parent.remove(child)
                return True
            # Check if wrapped in <item>
            if child.tag == 'item':
                for grandchild in list(child):
                    if grandchild.tag == 'widget' and grandchild.get('name') == widget_name:
                        parent.remove(child)
                        return True
    return False

# Find the top-level tabMLQC (the original one, NOT the one we just created inside tabQCInner)
# After our changes, there are now TWO tabMLQC widgets:
#   1. The one inside tabQCInner (which we just created)
#   2. The original top-level one still in centralTabWidget
#
# We need to remove #2. We know it's a direct child of a layout inside centralTabWidget.
# Let's find it by traversing directly from qc_parent (which is the parent of tabQualitycontrol)

def find_and_remove_toplevel_mlqc(root, already_moved_elem):
    """Remove the top-level tabMLQC (not the one we just moved into tabQCInner)."""
    for parent in root.iter():
        for i, child in enumerate(parent):
            if child.tag == 'widget' and child.get('name') == 'tabMLQC' and child is not already_moved_elem:
                parent.remove(child)
                print(f"Removed top-level tabMLQC from parent: {parent.tag} {parent.get('name', '')}")
                return True
            if child.tag == 'item':
                for grandchild in list(child):
                    if grandchild.tag == 'widget' and grandchild.get('name') == 'tabMLQC' and grandchild is not already_moved_elem:
                        parent.remove(child)
                        print(f"Removed top-level tabMLQC (wrapped in item) from parent: {parent.tag} {parent.get('name', '')}")
                        return True
    return False

removed = find_and_remove_toplevel_mlqc(root, tab_ml_inner)
if not removed:
    print("WARNING: Could not find/remove top-level tabMLQC")

# ── Verify the result ─────────────────────────────────────────────────────
ml_count = sum(1 for w in root.iter('widget') if w.get('name') == 'tabMLQC')
stat_count = sum(1 for w in root.iter('widget') if w.get('name') == 'tabQCStat')
inner_count = sum(1 for w in root.iter('widget') if w.get('name') == 'tabQCInner')
print(f"tabMLQC occurrences:  {ml_count} (expected 1)")
print(f"tabQCStat occurrences: {stat_count} (expected 1)")
print(f"tabQCInner occurrences: {inner_count} (expected 1)")

# ── Write back ────────────────────────────────────────────────────────────
tree.write(UI_PATH, xml_declaration=True, encoding='UTF-8', pretty_print=True)
print(f"Written to {UI_PATH}")

# Verify the written file is valid
import xml.etree.ElementTree as ET
try:
    ET.parse(UI_PATH)
    print("Output XML is valid!")
except ET.ParseError as e:
    print(f"Output XML has parse error: {e}")
