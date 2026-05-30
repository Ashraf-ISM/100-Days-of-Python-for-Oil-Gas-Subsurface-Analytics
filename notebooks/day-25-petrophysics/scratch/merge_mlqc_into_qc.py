"""
merge_mlqc_into_qc_v2.py
========================
Uses regex-based XML manipulation to merge tabMLQC into tabQualitycontrol
as an inner sub-tab in a new QTabWidget called tabQCInner.

Approach: Extract the raw XML blocks with a bracket-depth scanner,
then perform targeted string replacements.
"""

import re

UI_PATH = "/home/ashraf/Desktop/100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics-Well-log/notebooks/day-25-petrophysics/ui/mainwindow.ui"

with open(UI_PATH, encoding="utf-8") as f:
    content = f.read()

def find_widget_block(text, name):
    """
    Find the character offsets (start, end) of the <widget name="NAME"> block.
    Returns (start_char, end_char) inclusive of the closing </widget> tag.
    """
    # Find the opening tag
    pattern = rf'<widget[^>]*name="{re.escape(name)}"[^>]*>'
    m = re.search(pattern, text)
    if not m:
        raise RuntimeError(f"Widget {name!r} not found in file")
    start = m.start()
    pos = m.end()
    depth = 1
    while depth > 0 and pos < len(text):
        # Find next <widget or </widget
        next_open  = text.find('<widget',  pos)
        next_close = text.find('</widget>', pos)
        if next_close == -1:
            break
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + len('<widget')
        else:
            depth -= 1
            pos = next_close + len('</widget>')
    end = pos  # pos is right after the last </widget>
    return start, end

# ── Locate blocks ──────────────────────────────────────────────────────────
qc_start, qc_end = find_widget_block(content, "tabQualitycontrol")
ml_start, ml_end = find_widget_block(content, "tabMLQC")

print(f"tabQualitycontrol: chars {qc_start}–{qc_end}")
print(f"tabMLQC:           chars {ml_start}–{ml_end}")

qc_block = content[qc_start:qc_end]
ml_block = content[ml_start:ml_end]

# ── Extract the QC tab's inner layout ─────────────────────────────────────
# qc_block starts with <widget class="QWidget" name="tabQualitycontrol">
# then has <attribute name="title">...
# then has <layout ...> ... </layout>
# then </widget>
# We want everything between (not including) the first <layout and last </widget>

layout_start_in_qc = qc_block.find('<layout')
if layout_start_in_qc == -1:
    raise RuntimeError("No <layout found inside tabQualitycontrol")

# The layout and everything after it, up to but not including the final </widget>
qc_inner = qc_block[layout_start_in_qc : qc_block.rfind('</widget>')]

# The header: everything before the first <layout
qc_header = qc_block[:layout_start_in_qc]

# ── Extract ML QC tab's inner layout ──────────────────────────────────────
ml_layout_start = ml_block.find('<layout')
if ml_layout_start == -1:
    raise RuntimeError("No <layout found inside tabMLQC")
ml_inner = ml_block[ml_layout_start : ml_block.rfind('</widget>')]

# ── Build new combined tabQualitycontrol block ────────────────────────────
#
# The QC tab becomes:
#   <widget class="QWidget" name="tabQualitycontrol">
#     <attribute name="title">Quality Control</attribute>
#     <layout class="QVBoxLayout" name="layoutQCOuter">
#       <property name="spacing">...</property>
#       <item>
#         <widget class="QTabWidget" name="tabQCInner">
#           <widget class="QWidget" name="tabQCStat">
#             <attribute name="title">Statistical QC</attribute>
#             [original qc_inner – the QC layout]
#           </widget>
#           <widget class="QWidget" name="tabMLQC">
#             <attribute name="title">ML Based QC</attribute>
#             [ml_inner – the ML QC layout]
#           </widget>
#         </widget>
#       </item>
#     </layout>
#   </widget>

def reindent(text, extra_indent):
    """Prepend extra_indent to every non-blank line."""
    result = []
    for line in text.splitlines(keepends=True):
        if line.strip():
            result.append(extra_indent + line)
        else:
            result.append(line)
    return "".join(result)

# Re-indent inner content to account for the extra nesting
# (they will be inside tabQCStat / tabMLQC inside tabQCInner inside the new layout)
stat_inner_indented = reindent(qc_inner, "      ")   # 6 spaces extra
ml_inner_indented   = reindent(ml_inner, "      ")   # 6 spaces extra

new_qc_block = (
    qc_header  # includes opening <widget> tag and <attribute name="title">
    + '   <layout class="QVBoxLayout" name="layoutQCOuter">\n'
    + '    <property name="spacing"><number>0</number></property>\n'
    + '    <property name="leftMargin"><number>0</number></property>\n'
    + '    <property name="topMargin"><number>0</number></property>\n'
    + '    <property name="rightMargin"><number>0</number></property>\n'
    + '    <property name="bottomMargin"><number>0</number></property>\n'
    + '    <item>\n'
    + '     <widget class="QTabWidget" name="tabQCInner">\n'
    + '      <property name="tabPosition"><enum>QTabWidget::North</enum></property>\n'
    + '      <property name="currentIndex"><number>0</number></property>\n'
    # ── Sub-tab 1: Statistical QC ──
    + '      <widget class="QWidget" name="tabQCStat">\n'
    + '       <attribute name="title"><string>Statistical QC</string></attribute>\n'
    + stat_inner_indented + "\n"
    + '      </widget>\n'
    # ── Sub-tab 2: ML Based QC ──
    + '      <widget class="QWidget" name="tabMLQC">\n'
    + '       <attribute name="title"><string>ML Based QC</string></attribute>\n'
    + ml_inner_indented + "\n"
    + '      </widget>\n'
    + '     </widget>\n'
    + '    </item>\n'
    + '   </layout>\n'
    + '  </widget>'  # closing tag for tabQualitycontrol
)

# ── Replace tabQualitycontrol in the content ──────────────────────────────
new_content = content[:qc_start] + new_qc_block + content[qc_end:]

# ── Find and remove the now-orphaned top-level tabMLQC ────────────────────
# After our replacement, the tabMLQC widget is embedded inside tabQCInner.
# The original top-level tabMLQC still remains in new_content (it wasn't touched).
# We need to remove it.

# The original ml_start/ml_end positions are now SHIFTED by the replacement.
# Calculate shift:
shift = len(new_qc_block) - (qc_end - qc_start)
ml_start_new = ml_start + shift
ml_end_new   = ml_end   + shift

print(f"Removing orphan tabMLQC at chars {ml_start_new}–{ml_end_new}")

# Verify it's still tabMLQC
snippet = new_content[ml_start_new : ml_start_new + 80]
print(f"Snippet at ml_start_new: {snippet!r}")

# Only remove if it's the outer tabMLQC
if 'name="tabMLQC"' in snippet and '<widget' in snippet:
    final_content = new_content[:ml_start_new] + new_content[ml_end_new:]
    print("Orphan top-level tabMLQC removed.")
else:
    print("WARNING: Expected tabMLQC not at computed position. Searching manually...")
    # Fall-back: find the SECOND occurrence of tabMLQC widget
    first_occ = new_content.find('name="tabMLQC"')
    second_occ = new_content.find('name="tabMLQC"', first_occ + 1)
    if second_occ != -1:
        # Walk back to the <widget tag
        widget_start = new_content.rfind('<widget', 0, second_occ)
        _, orphan_end = find_widget_block(new_content[widget_start:], "tabMLQC")
        orphan_end_abs = widget_start + orphan_end
        final_content = new_content[:widget_start] + new_content[orphan_end_abs:]
        print(f"Fallback: removed orphan tabMLQC at chars {widget_start}–{orphan_end_abs}")
    else:
        print("No second tabMLQC found — content is already merged.")
        final_content = new_content

# ── Write output ──────────────────────────────────────────────────────────
with open(UI_PATH, "w", encoding="utf-8") as f:
    f.write(final_content)

print(f"Done — mainwindow.ui updated.")
print(f"Original size: {len(content)} chars")
print(f"Final size:    {len(final_content)} chars")
print(f"Change:        {len(final_content) - len(content):+d} chars")

# Quick sanity check: count tabMLQC occurrences
occurrences = len(re.findall(r'name="tabMLQC"', final_content))
print(f"tabMLQC occurrences in final file: {occurrences}")
occurrences_qcinner = len(re.findall(r'name="tabQCInner"', final_content))
print(f"tabQCInner occurrences in final file: {occurrences_qcinner}")
