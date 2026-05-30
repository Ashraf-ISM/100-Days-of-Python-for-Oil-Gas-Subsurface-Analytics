"""
merge_mlqc_into_qc.py
=====================
Merges the top-level tabMLQC into tabQualitycontrol as a sub-tab called
"ML Based QC" inside an inner QTabWidget.

Strategy:
1. Find tabQualitycontrol's content and wrap it in a sub-tab "Statistical QC"
2. Move tabMLQC (minus its outer <widget> shell) into a second sub-tab "ML Based QC"
3. Both sub-tabs live inside a new QTabWidget named "tabQCInner" in tabQualitycontrol
4. Remove the now-defunct top-level tabMLQC
"""

import re

UI_PATH = "/home/ashraf/Desktop/100-Days-of-Python-for-Oil-Gas-Subsurface-Analytics-Well-log/notebooks/day-25-petrophysics/ui/mainwindow.ui"

content = open(UI_PATH, encoding="utf-8").read()
lines = content.splitlines(keepends=True)

# ── 1. Locate tabQualitycontrol ────────────────────────────────────────────
def find_widget_bounds(lines, name):
    """Return (start_idx, end_idx) of the <widget name='name'> block (0-indexed)."""
    depth = 0
    start = None
    for i, line in enumerate(lines):
        if f'name="{name}"' in line and '<widget' in line:
            start = i
            depth = 0
        if start is not None:
            depth += line.count("<widget") + line.count("<layout") + line.count("<item") + line.count("<spacer")
            depth -= line.count("</widget>") + line.count("</layout>") + line.count("</item>") + line.count("</spacer>")
            if depth <= 0:
                return start, i
    raise RuntimeError(f"Widget {name!r} not found")

qc_start, qc_end = find_widget_bounds(lines, "tabQualitycontrol")
ml_start, ml_end = find_widget_bounds(lines, "tabMLQC")

print(f"tabQualitycontrol: lines {qc_start+1}–{qc_end+1}")
print(f"tabMLQC:           lines {ml_start+1}–{ml_end+1}")

# ── 2. Extract the QC tab's inner content ─────────────────────────────────
# tabQualitycontrol looks like:
#   <widget class="QWidget" name="tabQualitycontrol">
#     <attribute name="title"><string>Quality Control</string></attribute>
#     <layout ...>
#       ...content...
#     </layout>
#   </widget>
#
# We want to keep the outer widget shell but replace its layout children with
# a QTabWidget containing two sub-tabs.

qc_lines = lines[qc_start : qc_end + 1]

# Find the layout open tag (first <layout) and the matching close within qc_lines
layout_open_idx = None
for j, ln in enumerate(qc_lines):
    if "<layout" in ln:
        layout_open_idx = j
        break

# The layout content is everything from layout_open_idx to the second-to-last line
# (last line is </widget>)
# But we want to extract "inner content lines" = qc_lines[layout_open_idx : -1]
# We'll re-indent them to be inside a sub-tab

qc_inner = qc_lines[layout_open_idx : -1]   # layout + all content, excluding closing </widget>

# ── 3. Extract ML QC tab's inner layout content ───────────────────────────
# tabMLQC:
#   <widget class="QWidget" name="tabMLQC">
#     <attribute .../>
#     <layout ...>  ... </layout>
#   </widget>

ml_lines = lines[ml_start : ml_end + 1]

# Find layout inside tabMLQC
ml_layout_open = None
for j, ln in enumerate(ml_lines):
    if "<layout" in ln:
        ml_layout_open = j
        break

ml_inner = ml_lines[ml_layout_open : -1]  # layout + content, excluding </widget>

# ── 4. Build the new tabQualitycontrol content ────────────────────────────
# We replace the original layout inside tabQualitycontrol with:
#   <layout class="QVBoxLayout">
#     <item>
#       <widget class="QTabWidget" name="tabQCInner">
#         <widget class="QWidget" name="tabQCStat">
#           <attribute name="title"><string>Statistical QC</string></attribute>
#           [original QC layout content, re-indented]
#         </widget>
#         <widget class="QWidget" name="tabMLQC">
#           <attribute name="title"><string>ML Based QC</string></attribute>
#           [ML QC layout content, re-indented]
#         </widget>
#       </widget>
#     </item>
#   </layout>

EXTRA = "   "  # 3 extra spaces for the additional nesting inside sub-tab

def indent_lines(line_list, prefix):
    return [prefix + ln if ln.strip() else ln for ln in line_list]

stat_qc_sub = (
    '   <widget class="QWidget" name="tabQCStat">\n'
    '    <attribute name="title"><string>Statistical QC</string></attribute>\n'
)
stat_qc_sub += "".join(indent_lines(qc_inner, "    "))
stat_qc_sub += '   </widget>\n'

ml_qc_sub = (
    '   <widget class="QWidget" name="tabMLQC">\n'
    '    <attribute name="title"><string>ML Based QC</string></attribute>\n'
)
ml_qc_sub += "".join(indent_lines(ml_inner, "    "))
ml_qc_sub += '   </widget>\n'

new_qc_content = (
    '  <layout class="QVBoxLayout" name="layoutQCOuter">\n'
    '   <property name="spacing"><number>0</number></property>\n'
    '   <property name="leftMargin"><number>0</number></property>\n'
    '   <property name="topMargin"><number>0</number></property>\n'
    '   <property name="rightMargin"><number>0</number></property>\n'
    '   <property name="bottomMargin"><number>0</number></property>\n'
    '   <item>\n'
    '    <widget class="QTabWidget" name="tabQCInner">\n'
    '     <property name="tabPosition"><enum>QTabWidget::North</enum></property>\n'
    '     <property name="currentIndex"><number>0</number></property>\n'
    + "".join(indent_lines([stat_qc_sub], "     "))
    + "".join(indent_lines([ml_qc_sub], "     "))
    + '    </widget>\n'
    '   </item>\n'
    '  </layout>\n'
)

# The header for tabQualitycontrol (lines before the first <layout)
qc_header = "".join(qc_lines[:layout_open_idx])
new_qc_widget = (
    qc_header
    + new_qc_content
    + "".join(qc_lines[-1:])  # closing </widget>
)

# ── 5. Assemble the new file ───────────────────────────────────────────────
# Replace qc_start..qc_end with new_qc_widget
# Then remove ml_start..ml_end (the top-level tabMLQC)

# First: build new lines list with the new QC widget replacing the old one
new_lines = list(lines[:qc_start]) + [new_qc_widget] + list(lines[qc_end + 1 :])

# Now find tabMLQC in new_lines (it shifted)
ml_start2, ml_end2 = find_widget_bounds(new_lines, "tabMLQC")
# But tabMLQC now lives INSIDE tabQCInner – we need the TOP-LEVEL one.
# The top-level tabMLQC is the one that is a direct child of centralTabWidget.
# After our replacement, the inner tabMLQC is nested; the top-level one no longer exists.
# Actually wait – we *moved* tabMLQC's CONTENT, not the widget itself.
# The original top-level tabMLQC block (ml_start..ml_end in original) is still in new_lines
# because we only replaced qc_start..qc_end.  Find it again.

# Re-compute ml position in new_lines. The original tabMLQC is after qc_end in original,
# so in new_lines it starts after the new qc widget.

# Find the top-level tabMLQC: it should be a <widget name="tabMLQC"> that is a
# direct child of centralTabWidget — NOT nested inside tabQCInner.
# Since tabQCInner is our new widget, the inner tabMLQC will be found first if we
# scan from the start. The *outer* (to-be-removed) tabMLQC will appear *after* the
# entire qc widget block.

# Simple: find the SECOND occurrence of name="tabMLQC"
occurrences = []
for i, ln in enumerate(new_lines):
    if isinstance(ln, str):
        text = ln
    else:
        text = ln
    if 'name="tabMLQC"' in text and '<widget' in text:
        occurrences.append(i)

print(f"tabMLQC occurrences in new_lines: {[o+1 for o in occurrences]}")

if len(occurrences) >= 2:
    # The second one is the orphan top-level tabMLQC
    orphan_start = occurrences[1]
    _, orphan_end = find_widget_bounds(new_lines, "tabMLQC")
    # find_widget_bounds finds the FIRST – we need to find from occurrences[1]
    # Manually find the end
    depth = 0
    orphan_end2 = None
    for i in range(orphan_start, len(new_lines)):
        ln = new_lines[i] if isinstance(new_lines[i], str) else new_lines[i]
        depth += ln.count("<widget") + ln.count("<layout") + ln.count("<item") + ln.count("<spacer")
        depth -= ln.count("</widget>") + ln.count("</layout>") + ln.count("</item>") + ln.count("</spacer>")
        if depth <= 0:
            orphan_end2 = i
            break
    print(f"Removing orphan tabMLQC: lines {orphan_start+1}–{orphan_end2+1}")
    final_lines = new_lines[:orphan_start] + new_lines[orphan_end2 + 1:]
else:
    print("Only one tabMLQC found — already merged. No removal needed.")
    final_lines = new_lines

# ── 6. Write output ───────────────────────────────────────────────────────
result = "".join(
    (ln if isinstance(ln, str) else ln) for ln in final_lines
)

with open(UI_PATH, "w", encoding="utf-8") as f:
    f.write(result)

print("Done — mainwindow.ui updated.")
print(f"Final line count: {len(result.splitlines())}")
