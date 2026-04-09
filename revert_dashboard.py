import sys

with open('notebooks/day-25-petrophysics/ui/mainwindow.ui', 'r', encoding='utf-8') as f:
    lines = f.readlines()

original_dashboard = """   <widget class="QWidget" name="tabDashboard">
    <attribute name="title">
     <string>⌂ Dashboard</string>
    </attribute>
    <layout class="QVBoxLayout" name="layoutDashboard">
     <item>
      <widget class="QLabel" name="lblDashTitle">
       <property name="styleSheet">
        <string>font-size:18px;font-weight:700;color:#2A5090;padding:20px 0 6px 0;</string>
       </property>
       <property name="text">
        <string>PetroARX — Welcome</string>
       </property>
       <property name="alignment">
        <set>Qt::AlignHCenter|Qt::AlignTop</set>
       </property>
      </widget>
     </item>
     <item>
      <widget class="QLabel" name="lblDashSub">
       <property name="styleSheet">
        <string>font-size:13px;color:#4A6A8A;</string>
       </property>
       <property name="text">
        <string>Open a project or import LAS data to begin.  Use the toolbar or menus above to open any analysis module.</string>
       </property>
       <property name="alignment">
        <set>Qt::AlignHCenter</set>
       </property>
       <property name="wordWrap">
        <bool>true</bool>
       </property>
      </widget>
     </item>
     <item>
      <spacer name="spacerDashV">
       <property name="orientation">
        <enum>Qt::Vertical</enum>
       </property>
       <property name="sizeHint" stdset="0">
        <size>
         <width>20</width>
         <height>60</height>
        </size>
       </property>
      </spacer>
     </item>
     <item>
      <layout class="QHBoxLayout" name="layoutDashCards">
       <item>
        <widget class="QGroupBox" name="cardImport">
         <property name="title">
          <string>Quick Import</string>
         </property>
         <layout class="QVBoxLayout">
          <item>
           <widget class="QPushButton" name="btnDashImportLAS">
            <property name="text">
             <string>Import LAS File...</string>
            </property>
           </widget>
          </item>
          <item>
           <widget class="QPushButton" name="btnDashImportCSV">
            <property name="text">
             <string>Import CSV / Excel...</string>
            </property>
           </widget>
          </item>
          <item>
           <widget class="QPushButton" name="btnDashImportSEGY">
            <property name="text">
             <string>Import SEG-Y...</string>
            </property>
           </widget>
          </item>
         </layout>
        </widget>
       </item>
       <item>
        <widget class="QGroupBox" name="cardRecent">
         <property name="title">
          <string>Recent Projects</string>
         </property>
         <layout class="QVBoxLayout">
          <item>
           <widget class="QPushButton" name="btnDashRecent1">
            <property name="text">
             <string>SandboxMay2016</string>
            </property>
           </widget>
          </item>
          <item>
           <widget class="QPushButton" name="btnDashRecent2">
            <property name="text">
             <string>Field_A_EvalProject</string>
            </property>
           </widget>
          </item>
          <item>
           <widget class="QPushButton" name="btnDashRecent3">
            <property name="text">
             <string>OffshoreBlock_7</string>
            </property>
           </widget>
          </item>
         </layout>
        </widget>
       </item>
       <item>
        <widget class="QGroupBox" name="cardModules">
         <property name="title">
          <string>Open Module</string>
         </property>
         <layout class="QGridLayout">
          <item row="0" column="0">
           <widget class="QPushButton" name="btnDashLogView">
            <property name="text">
             <string>Log Viewer</string>
            </property>
           </widget>
          </item>
          <item row="0" column="1">
           <widget class="QPushButton" name="btnDashXplot">
            <property name="text">
             <string>Crossplot</string>
            </property>
           </widget>
          </item>
          <item row="1" column="0">
           <widget class="QPushButton" name="btnDashVsh">
            <property name="text">
             <string>Shale Volume</string>
            </property>
           </widget>
          </item>
          <item row="1" column="1">
           <widget class="QPushButton" name="btnDashSw">
            <property name="text">
             <string>Water Saturation</string>
            </property>
           </widget>
          </item>
          <item row="2" column="0">
           <widget class="QPushButton" name="btnDashGeo">
            <property name="text">
             <string>Geomechanics</string>
            </property>
           </widget>
          </item>
          <item row="2" column="1">
           <widget class="QPushButton" name="btnDashCorr">
            <property name="text">
             <string>Well Correlation</string>
            </property>
           </widget>
          </item>
         </layout>
        </widget>
       </item>
      </layout>
     </item>
     <item>
      <spacer name="spacerDashV2">
       <property name="orientation">
        <enum>Qt::Vertical</enum>
       </property>
       <property name="sizeHint" stdset="0">
        <size>
         <width>20</width>
         <height>40</height>
        </size>
       </property>
      </spacer>
     </item>
    </layout>
   </widget>
"""

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if '<widget class="QWidget" name="tabDashboard">' in line:
        start_idx = i
        break

if start_idx != -1:
    indent = lines[start_idx][:len(lines[start_idx]) - len(lines[start_idx].lstrip())]
    for i in range(start_idx + 1, len(lines)):
        if '<widget class="QWidget" name="tabLogViewer">' in lines[i]:
            for j in range(i-1, start_idx, -1):
                if lines[j].startswith(indent + "</widget>"):
                    end_idx = j
                    break
            break

if start_idx != -1 and end_idx != -1:
    new_lines = [line + "\n" if not line.endswith("\n") else line for line in original_dashboard.split('\n')]
    if new_lines[-1] == "\n":
        new_lines = new_lines[:-1]
    
    lines = lines[:start_idx] + new_lines + lines[end_idx+1:]
    
    with open('notebooks/day-25-petrophysics/ui/mainwindow.ui', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Successfully reverted tabDashboard!")
else:
    print(f"Could not find start/end indices: start_idx={start_idx}, end_idx={end_idx}")

