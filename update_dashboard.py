import sys

with open('notebooks/day-25-petrophysics/ui/mainwindow.ui', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_tab = """   <widget class="QWidget" name="tabDashboard">
    <attribute name="title">
     <string>⌂ Dashboard</string>
    </attribute>
    <layout class="QVBoxLayout" name="layoutDashboardMain">
     <property name="spacing"><number>18</number></property>
     <property name="margin"><number>18</number></property>
     
     <!-- Top Header Banner -->
     <item>
      <widget class="QFrame" name="frameDashHeader">
       <property name="styleSheet">
        <string>
         QFrame {
             background-color: #2F659F;
             border-radius: 8px;
         }
         QLabel#lblDashMainTitle { color: #FFFFFF; font-size: 22px; font-weight: bold; }
         QLabel#lblDashSub { font-size: 13px; color: #DDEEFF; }
        </string>
       </property>
       <layout class="QHBoxLayout">
        <property name="margin"><number>15</number></property>
        <item>
         <layout class="QVBoxLayout">
          <item><widget class="QLabel" name="lblDashMainTitle"><property name="text"><string>PetroARX Dashboard</string></property></widget></item>
          <item><widget class="QLabel" name="lblDashSub"><property name="text"><string>Quick overview of project activity, well status, and interpretation progress.</string></property></widget></item>
         </layout>
        </item>
        <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
        <item>
         <widget class="QComboBox" name="comboDashWorkspace">
          <property name="styleSheet"><string>background: white; color: #334155; border-radius: 4px; padding: 6px 12px; font-weight: 500;</string></property>
          <item><property name="text"><string>Entire Workspace...</string></property></item>
         </widget>
        </item>
       </layout>
      </widget>
     </item>
     
     <!-- Top Three Cards -->
     <item>
      <layout class="QHBoxLayout" name="layoutDashTopCards">
       <property name="spacing"><number>18</number></property>
       
       <!-- 1. Project Overview -->
       <item>
        <widget class="QFrame" name="cardProjectOverview">
         <property name="styleSheet">
          <string>
           QFrame { background: white; border: 1px solid #E2E8F0; border-radius: 8px; }
           QLabel { color: #334155; border: none; }
           QLabel.cardTitle { font-size: 16px; font-weight: bold; color: #1E293B; }
          </string>
         </property>
         <layout class="QVBoxLayout">
          <property name="margin"><number>15</number></property>
          <item><widget class="QLabel" name="lblTitlePO"><property name="text"><string>Project Overview</string></property><property name="styleSheet"><string>font-size: 16px; font-weight: bold;</string></property></widget></item>
          <item>
           <layout class="QGridLayout">
            <property name="verticalSpacing"><number>10</number></property>
            <item row="0" column="0"><widget class="QLabel"><property name="text"><string>+ Wells</string></property></widget></item>
            <item row="1" column="0"><widget class="QLabel"><property name="text"><string>9</string></property><property name="styleSheet"><string>font-size: 26px; font-weight: bold; color: #3b82f6;</string></property></widget></item>
            
            <item row="0" column="1"><widget class="QLabel"><property name="text"><string>⬡ Formations</string></property></widget></item>
            <item row="1" column="1"><widget class="QLabel"><property name="text"><string>3</string></property><property name="styleSheet"><string>font-size: 26px; font-weight: bold; color: #10B981;</string></property></widget></item>
            
            <item row="2" column="0"><widget class="QLabel"><property name="text"><string>☰ Curve Count</string></property></widget></item>
            <item row="3" column="0"><widget class="QLabel"><property name="text"><string>26</string></property><property name="styleSheet"><string>font-size: 20px; font-weight: bold;</string></property></widget></item>
            
            <item row="2" column="1"><widget class="QLabel"><property name="text"><string>◫ Current Samples</string></property></widget></item>
            <item row="3" column="1"><widget class="QLabel"><property name="text"><string>1,495</string></property><property name="styleSheet"><string>font-size: 20px; font-weight: bold;</string></property></widget></item>
           </layout>
          </item>
          <item><spacer><property name="orientation"><enum>Qt::Vertical</enum></property></spacer></item>
          <item><widget class="QLabel"><property name="text"><string>&lt;b&gt;Active Well:&lt;/b&gt; Georganichthy_1_suite3_supercombo</string></property></widget></item>
          <item><widget class="QLabel"><property name="text"><string>&lt;b&gt;Depth Range:&lt;/b&gt; 720 m - 2,340 m</string></property></widget></item>
         </layout>
        </widget>
       </item>

       <!-- 2. Data Quality Diagnostics -->
       <item>
        <widget class="QFrame" name="cardDataQuality">
         <property name="styleSheet">
          <string>
           QFrame { background: white; border: 1px solid #E2E8F0; border-radius: 8px; }
           QLabel { color: #334155; border: none; }
          </string>
         </property>
         <layout class="QVBoxLayout">
          <property name="margin"><number>15</number></property>
          <item><widget class="QLabel" name="lblTitleDQ"><property name="text"><string>Data Quality Diagnostics</string></property><property name="styleSheet"><string>font-size: 16px; font-weight: bold;</string></property></widget></item>
          <item>
           <layout class="QHBoxLayout">
            <item>
             <widget class="QLabel" name="dqCircle">
              <property name="text"><string>98%</string></property>
              <property name="alignment"><set>Qt::AlignCenter</set></property>
              <property name="minimumSize"><size><width>120</width><height>120</height></size></property>
              <property name="maximumSize"><size><width>120</width><height>120</height></size></property>
              <property name="styleSheet"><string>font-size: 32px; font-weight: bold; color: #10B981; border: 12px solid #10B981; border-radius: 60px; background: transparent;</string></property>
             </widget>
            </item>
            <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property><property name="sizeType"><enum>QSizePolicy::Fixed</enum></property><property name="sizeHint"><size><width>20</width><height>20</height></size></property></spacer></item>
            <item>
             <layout class="QVBoxLayout">
              <item><layout class="QHBoxLayout"><item><widget class="QLabel"><property name="text"><string>Missing Values</string></property></widget></item><item><widget class="QLabel"><property name="text"><string>2%</string></property><property name="alignment"><set>Qt::AlignRight</set></property><property name="styleSheet"><string>font-weight: bold; color: #10B981;</string></property></widget></item></layout></item>
              <item><widget class="Line"><property name="orientation"><enum>Qt::Horizontal</enum></property><property name="styleSheet"><string>color:#E2E8F0;</string></property></widget></item>
              <item><layout class="QHBoxLayout"><item><widget class="QLabel"><property name="text"><string>Outliers Detected</string></property></widget></item><item><widget class="QLabel"><property name="text"><string>12</string></property><property name="alignment"><set>Qt::AlignRight</set></property><property name="styleSheet"><string>font-weight: bold; color: #EF4444;</string></property></widget></item></layout></item>
              <item><widget class="Line"><property name="orientation"><enum>Qt::Horizontal</enum></property><property name="styleSheet"><string>color:#E2E8F0;</string></property></widget></item>
              <item><layout class="QHBoxLayout"><item><widget class="QLabel"><property name="text"><string>Depth Mismatch</string></property></widget></item><item><widget class="QLabel"><property name="text"><string>0</string></property><property name="alignment"><set>Qt::AlignRight</set></property><property name="styleSheet"><string>font-weight: bold;</string></property></widget></item></layout></item>
              <item><widget class="Line"><property name="orientation"><enum>Qt::Horizontal</enum></property><property name="styleSheet"><string>color:#E2E8F0;</string></property></widget></item>
              <item><layout class="QHBoxLayout"><item><widget class="QLabel"><property name="text"><string>Logs QC Count</string></property></widget></item><item><widget class="QLabel"><property name="text"><string>26</string></property><property name="alignment"><set>Qt::AlignRight</set></property><property name="styleSheet"><string>font-weight: bold; color: #3B82F6;</string></property></widget></item></layout></item>
             </layout>
            </item>
           </layout>
          </item>
          <item><spacer><property name="orientation"><enum>Qt::Vertical</enum></property></spacer></item>
          <item>
           <layout class="QHBoxLayout">
            <item><widget class="QLabel"><property name="text"><string>⚠️ Missing Values     🚫 Outliers Detected</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
            <item><widget class="QLabel"><property name="text"><string>&lt;b&gt;12   &gt;&lt;/b&gt;</string></property></widget></item>
           </layout>
          </item>
         </layout>
        </widget>
       </item>

       <!-- 3. Interpretation Overview -->
       <item>
        <widget class="QFrame" name="cardInterpretationOverview">
         <property name="styleSheet">
          <string>
           QFrame { background: white; border: 1px solid #E2E8F0; border-radius: 8px; }
           QLabel { color: #334155; border: none; }
          </string>
         </property>
         <layout class="QVBoxLayout">
          <property name="margin"><number>15</number></property>
          <item><widget class="QLabel" name="lblTitleIO"><property name="text"><string>Interpretation Overview</string></property><property name="styleSheet"><string>font-size: 16px; font-weight: bold;</string></property></widget></item>
          <item>
           <layout class="QGridLayout">
            <property name="verticalSpacing"><number>12</number></property>
            <item row="0" column="0"><widget class="QLabel"><property name="text"><string>Avg CTes</string></property></widget></item>
            <item row="0" column="1"><widget class="QLabel"><property name="text"><string>▂▃▄▅</string></property><property name="styleSheet"><string>color: #3B82F6;</string></property></widget></item>
            <item row="0" column="2"><widget class="QLabel"><property name="text"><string>0.25</string></property><property name="alignment"><set>Qt::AlignRight|Qt::AlignVCenter</set></property><property name="styleSheet"><string>font-size: 18px; font-weight: bold; color: #10B981;</string></property></widget></item>

            <item row="1" column="0"><widget class="QLabel"><property name="text"><string>Avg Porosity</string></property></widget></item>
            <item row="1" column="1"><widget class="QLabel"><property name="text"><string>▃▅▇▅▃</string></property><property name="styleSheet"><string>color: #0EA5E9;</string></property></widget></item>
            <item row="1" column="2"><widget class="QLabel"><property name="text"><string>0.19</string></property><property name="alignment"><set>Qt::AlignRight|Qt::AlignVCenter</set></property><property name="styleSheet"><string>font-size: 18px; font-weight: bold; color: #10B981;</string></property></widget></item>

            <item row="2" column="0"><widget class="QLabel"><property name="text"><string>Avg Sw</string></property></widget></item>
            <item row="2" column="1"><widget class="QLabel"><property name="text"><string>▇▆▄▃▂</string></property><property name="styleSheet"><string>color: #3B82F6;</string></property></widget></item>
            <item row="2" column="2"><widget class="QLabel"><property name="text"><string>0.34</string></property><property name="alignment"><set>Qt::AlignRight|Qt::AlignVCenter</set></property><property name="styleSheet"><string>font-size: 18px; font-weight: bold; color: #10B981;</string></property></widget></item>

            <item row="3" column="0"><widget class="QLabel"><property name="text"><string>Net Pay</string></property></widget></item>
            <item row="3" column="1"><widget class="QLabel"><property name="text"><string>183 m</string></property><property name="alignment"><set>Qt::AlignRight|Qt::AlignVCenter</set></property></widget></item>
            <item row="3" column="2"><widget class="QLabel"><property name="text"><string>183 m</string></property><property name="alignment"><set>Qt::AlignRight|Qt::AlignVCenter</set></property><property name="styleSheet"><string>font-size: 16px; font-weight: bold; color: #10B981;</string></property></widget></item>

            <item row="4" column="0"><widget class="QLabel"><property name="text"><string>Gross Thickness</string></property></widget></item>
            <item row="4" column="1"><widget class="QLabel"><property name="text"><string>256 m</string></property><property name="alignment"><set>Qt::AlignRight|Qt::AlignVCenter</set></property></widget></item>
            <item row="4" column="2"><widget class="QLabel"><property name="text"><string>0.72</string></property><property name="alignment"><set>Qt::AlignRight|Qt::AlignVCenter</set></property><property name="styleSheet"><string>font-size: 16px; font-weight: bold;</string></property></widget></item>
           </layout>
          </item>
          <item><widget class="Line"><property name="orientation"><enum>Qt::Horizontal</enum></property><property name="styleSheet"><string>color:#E2E8F0;</string></property></widget></item>
          <item>
           <layout class="QHBoxLayout">
            <item><widget class="QLabel"><property name="text"><string>Estimated Hydrocarbon Pay</string></property></widget></item>
            <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
            <item><widget class="QLabel"><property name="text"><string>107 m</string></property><property name="styleSheet"><string>font-size: 16px; font-weight: bold;</string></property></widget></item>
           </layout>
          </item>
         </layout>
        </widget>
       </item>
      </layout>
     </item>

     <!-- Interpretation Workflow Middle Row -->
     <item>
      <widget class="QFrame" name="cardWorkflow">
       <property name="styleSheet">
        <string>
         QFrame { background: white; border: 1px solid #E2E8F0; border-radius: 8px; }
         QLabel { color: #334155; border: none; }
         QPushButton { border: none; border-radius: 4px; padding: 12px; font-weight: bold; font-size: 13px; color: white; }
        </string>
       </property>
       <layout class="QVBoxLayout">
        <property name="margin"><number>18</number></property>
        <item>
         <layout class="QHBoxLayout">
          <item><widget class="QLabel"><property name="text"><string>Interpretation Workflow</string></property><property name="styleSheet"><string>font-size: 16px; font-weight: bold; color: #1E293B;</string></property></widget></item>
          <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
          <item><widget class="QLabel"><property name="text"><string>&gt;&gt;</string></property><property name="styleSheet"><string>color: #94A3B8; font-weight: bold;</string></property></widget></item>
         </layout>
        </item>
        
        <item>
         <layout class="QHBoxLayout">
          <property name="spacing"><number>12</number></property>
          <item><widget class="QPushButton"><property name="text"><string>⬇ Import Data &gt;</string></property><property name="styleSheet"><string>background: #2563EB;</string></property></widget></item>
          <item><widget class="QPushButton"><property name="text"><string>↻ Quality Control &gt;</string></property><property name="styleSheet"><string>background: #0EA5E9;</string></property></widget></item>
          <item><widget class="QPushButton"><property name="text"><string>Vshale &gt;</string></property><property name="styleSheet"><string>background: #10B981;</string></property></widget></item>
          <item><widget class="QPushButton"><property name="text"><string>📄 Porosity &gt;</string></property><property name="styleSheet"><string>background: #F97316;</string></property></widget></item>
          <item><widget class="QPushButton"><property name="text"><string>💧 Water Saturation &gt;</string></property><property name="styleSheet"><string>background: #F59E0B;</string></property></widget></item>
         </layout>
        </item>
        
        <item>
         <layout class="QHBoxLayout">
          <item><widget class="QLabel"><property name="text"><string>✓ Complete</string></property><property name="styleSheet"><string>color: #10B981; font-weight: bold;</string></property></widget></item>
          <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
          <item><widget class="QLabel"><property name="text"><string>✓ Complete</string></property><property name="styleSheet"><string>color: #10B981; font-weight: bold;</string></property></widget></item>
          <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
          <item><widget class="QLabel"><property name="text"><string>◷ 5 minutes ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
          <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
          <item><widget class="QLabel"><property name="text"><string>◷ 2 minutes ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
          <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
          <item><widget class="QLabel"><property name="text"><string>◷ 2 minutes ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
          <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
         </layout>
        </item>
       </layout>
      </widget>
     </item>

     <!-- Bottom Row -->
     <item>
      <layout class="QHBoxLayout" name="layoutDashBottomCards">
       <property name="spacing"><number>18</number></property>
       
       <item>
        <widget class="QFrame" name="cardRecentResults">
         <property name="styleSheet">
          <string>
           QFrame { background: white; border: 1px solid #E2E8F0; border-radius: 8px; }
           QLabel { color: #334155; border: none; }
          </string>
         </property>
         <layout class="QVBoxLayout">
          <property name="margin"><number>15</number></property>
          <item>
           <layout class="QHBoxLayout">
            <item><widget class="QLabel"><property name="text"><string>Recent Results</string></property><property name="styleSheet"><string>font-size: 16px; font-weight: bold; color: #1E293B;</string></property></widget></item>
            <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
            <item><widget class="QLabel"><property name="text"><string>&gt;&gt;</string></property><property name="styleSheet"><string>color: #94A3B8; font-weight: bold;</string></property></widget></item>
           </layout>
          </item>
          <item>
           <layout class="QGridLayout">
            <property name="verticalSpacing"><number>12</number></property>
            <item row="0" column="0"><widget class="QLabel"><property name="text"><string>📄 Shale Volume</string></property><property name="styleSheet"><string>font-weight: bold;</string></property></widget></item>
            <item row="1" column="0"><widget class="QLabel"><property name="text"><string>Log Viewer</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            <item row="0" column="1"><widget class="QLabel"><property name="text"><string>Log Created</string></property><property name="styleSheet"><string>color: #10B981;</string></property></widget></item>
            <item row="1" column="1"><widget class="QLabel"><property name="text"><string>5 min ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            
            <item row="0" column="2"><widget class="QLabel"><property name="text"><string>📊 Log Viewer</string></property><property name="styleSheet"><string>font-weight: bold;</string></property></widget></item>
            <item row="1" column="2"><widget class="QLabel"><property name="text"><string>Share Calculation</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            <item row="0" column="3"><widget class="QLabel"><property name="text"><string>5 min ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            <item row="1" column="3"><widget class="QLabel"><property name="text"><string>10 min ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            
            <item row="0" column="4"><widget class="QLabel"><property name="text"><string>⚙️ Vshale Calculation Completed</string></property><property name="styleSheet"><string>font-weight: bold;</string></property></widget></item>
            <item row="1" column="4"><widget class="QLabel"><property name="text"><string>Quality Control</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            <item row="0" column="5"><widget class="QLabel"><property name="text"><string>10 min ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            <item row="1" column="5"><widget class="QLabel"><property name="text"><string>24 min ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            
            <item row="2" column="0" colspan="2"><widget class="QLabel"><property name="text"><string>🗂️ GC Passed For 26 Curves</string></property><property name="styleSheet"><string>font-weight: bold;</string></property></widget></item>
            <item row="2" column="2" colspan="2"><widget class="QLabel"><property name="text"><string>Quality Control</string></property><property name="styleSheet"><string>color: #64748B;</string></property></widget></item>
            <item row="2" column="4" colspan="2"><widget class="QLabel"><property name="text"><string>⬇ Recent Activity</string></property><property name="styleSheet"><string>font-weight: bold;</string></property></widget></item>
           </layout>
          </item>
         </layout>
        </widget>
       </item>

       <item>
        <widget class="QFrame" name="cardRecentActivity">
         <property name="styleSheet">
          <string>
           QFrame { background: white; border: 1px solid #E2E8F0; border-radius: 8px; }
           QLabel { color: #334155; border: none; }
          </string>
         </property>
         <layout class="QVBoxLayout">
          <property name="margin"><number>15</number></property>
          <item><widget class="QLabel"><property name="text"><string>Recent Activity</string></property><property name="styleSheet"><string>font-size: 16px; font-weight: bold; color: #1E293B;</string></property></widget></item>
          <item>
           <layout class="QVBoxLayout">
            <property name="spacing"><number>2</number></property>
            <item><widget class="QLabel"><property name="text"><string>&lt;b&gt;✓ Last Opened Well&lt;/b&gt;</string></property></widget></item>
            <item><layout class="QHBoxLayout"><item><widget class="QLabel"><property name="text"><string>Georganichthy_1_suite3_supercemebo</string></property></widget></item><item><widget class="QLabel"><property name="text"><string>5 min ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property><property name="alignment"><set>Qt::AlignRight</set></property></widget></item></layout></item>
           </layout>
          </item>
          <item><widget class="Line"><property name="orientation"><enum>Qt::Horizontal</enum></property><property name="styleSheet"><string>color:#E2E8F0;</string></property></widget></item>
          <item>
           <layout class="QVBoxLayout">
            <property name="spacing"><number>2</number></property>
            <item><widget class="QLabel"><property name="text"><string>&lt;b&gt;⚙ Last Calculation Run&lt;/b&gt;</string></property></widget></item>
            <item><layout class="QHBoxLayout"><item><widget class="QLabel"><property name="text"><string>Sw Calculation</string></property></widget></item><item><widget class="QLabel"><property name="text"><string>2 min ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property><property name="alignment"><set>Qt::AlignRight</set></property></widget></item></layout></item>
           </layout>
          </item>
          <item><widget class="Line"><property name="orientation"><enum>Qt::Horizontal</enum></property><property name="styleSheet"><string>color:#E2E8F0;</string></property></widget></item>
          <item>
           <layout class="QVBoxLayout">
            <property name="spacing"><number>2</number></property>
            <item><widget class="QLabel"><property name="text"><string>&lt;b&gt;⬇ Last Exported Report&lt;/b&gt;</string></property></widget></item>
            <item><layout class="QHBoxLayout"><item><widget class="QLabel"><property name="text"><string>PetroARX_Report_040924.pdf</string></property></widget></item><item><widget class="QLabel"><property name="text"><string>1 hour ago</string></property><property name="styleSheet"><string>color: #64748B;</string></property><property name="alignment"><set>Qt::AlignRight</set></property></widget></item></layout></item>
           </layout>
          </item>
          <item><widget class="Line"><property name="orientation"><enum>Qt::Horizontal</enum></property><property name="styleSheet"><string>color:#E2E8F0;</string></property></widget></item>
          <item>
           <layout class="QVBoxLayout">
            <property name="spacing"><number>2</number></property>
            <item><widget class="QLabel"><property name="text"><string>&lt;b&gt;⚠️ Recent Warning&lt;/b&gt;</string></property><property name="styleSheet"><string>color: #F59E0B;</string></property></widget></item>
            <item><widget class="QLabel"><property name="text"><string>Depth mismatch detected on well GC4</string></property></widget></item>
           </layout>
          </item>
         </layout>
        </widget>
       </item>

      </layout>
     </item>
     
     <item>
      <spacer name="spacerDashboardBottom">
       <property name="orientation"><enum>Qt::Vertical</enum></property>
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
    
    # Needs to match the end of the widget specifically for this tab.
    # The previous code for tabDashboard had:
    # 488:    <widget class="QWidget" name="tabDashboard">
    # it ends before `<widget class="QWidget" name="tabLogViewer">`
    for i in range(start_idx + 1, len(lines)):
        if '<widget class="QWidget" name="tabLogViewer">' in lines[i]:
            for j in range(i-1, start_idx, -1):
                if lines[j].startswith(indent + "</widget>"):
                    end_idx = j
                    break
            break

if start_idx != -1 and end_idx != -1:
    new_lines = [line + "\n" if not line.endswith("\n") else line for line in new_tab.split('\n')]
    if new_lines[-1] == "\n":
        new_lines = new_lines[:-1]
    
    lines = lines[:start_idx] + new_lines + lines[end_idx+1:]
    
    with open('notebooks/day-25-petrophysics/ui/mainwindow.ui', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Successfully replaced tabDashboard!")
else:
    print(f"Could not find start/end indices: start_idx={start_idx}, end_idx={end_idx}")

