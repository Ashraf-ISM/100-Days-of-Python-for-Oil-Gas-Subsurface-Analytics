import sys

with open('notebooks/day-25-petrophysics/ui/mainwindow.ui', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_wbs_tab = """   <widget class="QWidget" name="tabWellboreStability">
    <attribute name="title">
     <string>Wellbore Stability</string>
    </attribute>
    <layout class="QVBoxLayout" name="layoutWBS_Main">
     <property name="spacing">
      <number>10</number>
     </property>
     <property name="margin">
      <number>10</number>
     </property>
     <item>
      <widget class="QFrame" name="frameWBSHeader">
       <property name="styleSheet">
        <string>
         QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; }
         QLabel { color: #1E293B; font-weight: 600; font-size: 14px; }
         QPushButton { background-color: #3B82F6; color: white; border: none; border-radius: 4px; padding: 6px 12px; font-weight: 600; }
         QPushButton:hover { background-color: #2563EB; }
         QPushButton#btnWBSExport { background-color: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; }
         QPushButton#btnWBSExport:hover { background-color: #E2E8F0; }
        </string>
       </property>
       <layout class="QHBoxLayout" name="layoutWBSHeader">
        <item>
         <widget class="QLabel" name="lblWBSTitle">
          <property name="text"><string>Advanced Wellbore Stability Analysis</string></property>
         </widget>
        </item>
        <item>
         <spacer name="spacerWBSHeader">
          <property name="orientation"><enum>Qt::Horizontal</enum></property>
         </spacer>
        </item>
        <item>
         <widget class="QPushButton" name="btnWBSRun">
          <property name="text"><string>▶ Run Analysis</string></property>
         </widget>
        </item>
        <item>
         <widget class="QPushButton" name="btnWBSExport">
          <property name="text"><string>⤓ Export Report</string></property>
         </widget>
        </item>
       </layout>
      </widget>
     </item>
     <item>
      <widget class="QSplitter" name="splitterWBS">
       <property name="orientation"><enum>Qt::Horizontal</enum></property>
       <widget class="QScrollArea" name="scrollWBSParams">
        <property name="widgetResizable"><bool>true</bool></property>
        <property name="styleSheet">
         <string>
          QScrollArea { border: none; background-color: #FFFFFF; }
          QGroupBox { font-size: 12px; font-weight: bold; color: #334155; border: 1px solid #E2E8F0; border-radius: 6px; margin-top: 10px; padding-top: 15px; }
          QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 5px; color: #3B82F6; }
          QLabel { color: #475569; font-weight: normal; }
         </string>
        </property>
        <widget class="QWidget" name="scrollWBSParamsContent">
         <layout class="QVBoxLayout" name="layoutWBSParamsContent">
          <item>
           <widget class="QGroupBox" name="groupWBSWellSelect">
            <property name="title"><string>Well &amp; Core Data</string></property>
            <layout class="QFormLayout" name="formWBSWell">
             <item row="0" column="0"><widget class="QLabel"><property name="text"><string>Well Context:</string></property></widget></item>
             <item row="0" column="1">
              <widget class="QComboBox" name="comboWBSWell">
               <item><property name="text"><string>CHr-1</string></property></item>
              </widget>
             </item>
            </layout>
           </widget>
          </item>
          <item>
           <widget class="QGroupBox" name="groupWBSGeomech">
            <property name="title"><string>Geomechanics Models</string></property>
            <layout class="QFormLayout" name="formWBSGeomech">
             <item row="0" column="0"><widget class="QLabel"><property name="text"><string>UCS Model:</string></property></widget></item>
             <item row="0" column="1">
              <widget class="QComboBox" name="comboWBSUCS">
               <item><property name="text"><string>Chang et al. (2006)</string></property></item>
               <item><property name="text"><string>Bradford et al.</string></property></item>
               <item><property name="text"><string>Custom Empirical...</string></property></item>
              </widget>
             </item>
             <item row="1" column="0"><widget class="QLabel"><property name="text"><string>Failure Criterion:</string></property></widget></item>
             <item row="1" column="1">
              <widget class="QComboBox" name="comboWBSFailure">
               <item><property name="text"><string>Mohr-Coulomb</string></property></item>
               <item><property name="text"><string>Modified Lade</string></property></item>
               <item><property name="text"><string>Mogi-Coulomb</string></property></item>
               <item><property name="text"><string>Drucker-Prager</string></property></item>
              </widget>
             </item>
             <item row="2" column="0"><widget class="QLabel"><property name="text"><string>Pore Pressure:</string></property></widget></item>
             <item row="2" column="1">
              <widget class="QComboBox" name="comboWBSPP">
               <item><property name="text"><string>PP_Eaton</string></property></item>
               <item><property name="text"><string>PP_Bowers</string></property></item>
              </widget>
             </item>
            </layout>
           </widget>
          </item>
          <item>
           <widget class="QGroupBox" name="groupWBSStresses">
            <property name="title"><string>In-situ Stresses</string></property>
            <layout class="QFormLayout" name="formWBSStress">
             <item row="0" column="0"><widget class="QLabel"><property name="text"><string>Sv Gradient (psi/ft):</string></property></widget></item>
             <item row="0" column="1">
              <widget class="QDoubleSpinBox" name="spinWBSSv">
               <property name="decimals"><number>4</number></property>
               <property name="value"><double>0.9500</double></property>
              </widget>
             </item>
             <item row="1" column="0"><widget class="QLabel"><property name="text"><string>SHmax Azimuth (°):</string></property></widget></item>
             <item row="1" column="1">
              <widget class="QDoubleSpinBox" name="spinWBSSHaz">
               <property name="maximum"><double>360.00</double></property>
               <property name="value"><double>45.00</double></property>
              </widget>
             </item>
             <item row="2" column="0"><widget class="QLabel"><property name="text"><string>Well Trajectory:</string></property></widget></item>
             <item row="2" column="1">
              <widget class="QPushButton" name="btnWBSTraj">
               <property name="text"><string>Load Deviation Survey...</string></property>
              </widget>
             </item>
            </layout>
           </widget>
          </item>
          <item>
           <spacer name="spacerWBSParams">
            <property name="orientation"><enum>Qt::Vertical</enum></property>
           </spacer>
          </item>
         </layout>
        </widget>
       </widget>
       <widget class="QWidget" name="widgetWBSDisplay">
        <layout class="QVBoxLayout" name="layoutWBSDisplay">
         <property name="margin"><number>0</number></property>
         <item>
          <widget class="QTabWidget" name="tabWBSCanvasTabs">
           <property name="styleSheet">
            <string>
             QTabWidget::pane { border: 1px solid #E2E8F0; border-radius: 4px; background: #FFFFFF; }
             QTabBar::tab { background: #F1F5F9; color: #64748B; padding: 8px 16px; border: 1px solid #E2E8F0; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; font-weight: 500; }
             QTabBar::tab:selected { background: #FFFFFF; color: #3B82F6; border-top: 2px solid #3B82F6; }
             QTabBar::tab:hover:!selected { background: #E2E8F0; color: #1E293B; }
            </string>
           </property>
           <widget class="QWidget" name="tabWBSMudWindow">
            <attribute name="title"><string>Mud Weight Window</string></attribute>
            <layout class="QVBoxLayout">
             <item>
              <widget class="QFrame" name="frameWBSCanvas">
               <property name="frameShape"><enum>QFrame::StyledPanel</enum></property>
               <layout class="QVBoxLayout">
                <item>
                 <widget class="QLabel" name="lblWBSPlaceholder">
                  <property name="styleSheet"><string>color:#94A3B8; font-size:14px; font-style:italic;</string></property>
                  <property name="text"><string>Interactive Mud Weight Window &amp; Breakout Plot Canvas...</string></property>
                  <property name="alignment"><set>Qt::AlignCenter</set></property>
                 </widget>
                </item>
               </layout>
              </widget>
             </item>
            </layout>
           </widget>
           <widget class="QWidget" name="tabWBSPolar">
            <attribute name="title"><string>Polar Plot (Stereonet)</string></attribute>
            <layout class="QVBoxLayout">
             <item>
              <widget class="QFrame" name="frameWBSPolarCanvas">
               <property name="frameShape"><enum>QFrame::StyledPanel</enum></property>
               <layout class="QVBoxLayout">
                <item>
                 <widget class="QLabel" name="lblWBSPolarPlaceholder">
                  <property name="styleSheet"><string>color:#94A3B8; font-size:14px; font-style:italic;</string></property>
                  <property name="text"><string>Wellbore Trajectory Polar Plot...</string></property>
                  <property name="alignment"><set>Qt::AlignCenter</set></property>
                 </widget>
                </item>
               </layout>
              </widget>
             </item>
            </layout>
           </widget>
          </widget>
         </item>
        </layout>
       </widget>
      </widget>
     </item>
    </layout>
   </widget>
"""

# find the start and end of tabWellboreStability using strings
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if '<widget class="QWidget" name="tabWellboreStability">' in line:
        start_idx = i
        break

if start_idx != -1:
    # find exactly the closing </widget> matching this indentation
    indent = lines[start_idx][:len(lines[start_idx]) - len(lines[start_idx].lstrip())]
    for i in range(start_idx + 1, len(lines)):
        if lines[i] == indent + "</widget>\n":
            end_idx = i
            break

if start_idx != -1 and end_idx != -1:
    new_wbs_lines = [line + "\n" if not line.endswith("\n") else line for line in new_wbs_tab.split('\n')]
    # drop empty string at end if there
    if new_wbs_lines[-1] == "\n":
        new_wbs_lines = new_wbs_lines[:-1]
    lines = lines[:start_idx] + new_wbs_lines + lines[end_idx+1:]
    
    with open('notebooks/day-25-petrophysics/ui/mainwindow.ui', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Successfully replaced Wellbore Stability tab")
else:
    print(f"Could not find start/end indices: start_idx={start_idx}, end_idx={end_idx}")

