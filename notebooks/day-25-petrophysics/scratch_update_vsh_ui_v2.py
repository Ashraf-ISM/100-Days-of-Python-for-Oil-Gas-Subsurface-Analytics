import xml.etree.ElementTree as ET

xml_file = "ui/mainwindow.ui"
tree = ET.parse(xml_file)
root = tree.getroot()

tab_vsh = None
for widget in root.iter("widget"):
    if widget.get("name") == "tabShaleVolume":
        tab_vsh = widget
        break

if tab_vsh is None:
    print("Could not find tabShaleVolume")
    exit(1)

# Find groupVshAge or lblVshAge and remove them, and update comboVclMethod
for layout in list(tab_vsh):
    if layout.tag == "layout" and layout.get("name") == "horzLayoutVshMain":
        tab_vsh.remove(layout)

new_layout_xml = """
   <layout class="QHBoxLayout" name="horzLayoutVshMain">
    <item>
     <!-- LEFT COLUMN -->
     <layout class="QVBoxLayout" name="layoutVshLeftColumn">
      <item>
       <widget class="QGroupBox" name="groupVshInputParameters">
        <property name="title"><string>INPUT PARAMETERS</string></property>
        <layout class="QFormLayout" name="formVshInput">
         <item row="0" column="0"><widget class="QLabel" name="lblVshWell"><property name="text"><string>Well</string></property></widget></item>
         <item row="0" column="1"><widget class="QComboBox" name="comboVclWell" /></item>
         
         <item row="1" column="0"><widget class="QLabel" name="lblVshGrCurve"><property name="text"><string>GR Curve</string></property></widget></item>
         <item row="1" column="1"><widget class="QComboBox" name="comboVclGR" /></item>

         <item row="2" column="0" colspan="2">
          <widget class="QGroupBox" name="groupVshBaseline">
           <property name="title"><string>Baseline Selection</string></property>
           <layout class="QVBoxLayout" name="layoutVshBaseline">
            <item>
             <layout class="QHBoxLayout" name="layoutVshRadios">
              <item><widget class="QRadioButton" name="rdoBaselineManual"><property name="text"><string>Manual</string></property></widget></item>
              <item><widget class="QRadioButton" name="rdoBaselineAuto"><property name="text"><string>Auto (Percentile)</string></property><property name="checked"><bool>true</bool></property></widget></item>
              <item><widget class="QRadioButton" name="rdoBaselineHist"><property name="text"><string>Histogram Peak</string></property></widget></item>
             </layout>
            </item>
            <item>
             <layout class="QHBoxLayout" name="layoutVshBaselineVals">
              <item>
               <widget class="QFrame" name="frameGrCleanInput">
                <property name="styleSheet"><string>background-color: #E8F5E9; border-radius: 5px;</string></property>
                <layout class="QVBoxLayout">
                 <item><widget class="QLabel"><property name="text"><string>GR Clean (Sand Line)</string></property></widget></item>
                 <item>
                  <layout class="QHBoxLayout">
                   <item><widget class="QDoubleSpinBox" name="spinVclGRmin"><property name="maximum"><double>999.0</double></property></widget></item>
                   <item><widget class="QLabel"><property name="text"><string>API</string></property></widget></item>
                  </layout>
                 </item>
                 <item>
                  <layout class="QHBoxLayout">
                   <item><widget class="QPushButton" name="btnAutoGrClean"><property name="text"><string>Auto</string></property></widget></item>
                   <item><widget class="QPushButton" name="btnPickGrClean"><property name="text"><string>Pick</string></property></widget></item>
                  </layout>
                 </item>
                </layout>
               </widget>
              </item>
              <item>
               <widget class="QFrame" name="frameGrShaleInput">
                <property name="styleSheet"><string>background-color: #FBE9E7; border-radius: 5px;</string></property>
                <layout class="QVBoxLayout">
                 <item><widget class="QLabel"><property name="text"><string>GR Shale (Shale Line)</string></property></widget></item>
                 <item>
                  <layout class="QHBoxLayout">
                   <item><widget class="QDoubleSpinBox" name="spinVclGRmax"><property name="maximum"><double>999.0</double></property></widget></item>
                   <item><widget class="QLabel"><property name="text"><string>API</string></property></widget></item>
                  </layout>
                 </item>
                 <item>
                  <layout class="QHBoxLayout">
                   <item><widget class="QPushButton" name="btnAutoGrShale"><property name="text"><string>Auto</string></property></widget></item>
                   <item><widget class="QPushButton" name="btnPickGrShale"><property name="text"><string>Pick</string></property></widget></item>
                  </layout>
                 </item>
                </layout>
               </widget>
              </item>
             </layout>
            </item>
           </layout>
          </widget>
         </item>

         <item row="3" column="0"><widget class="QLabel" name="lblVshMethod"><property name="text"><string>Shale Volume Method</string></property></widget></item>
         <item row="3" column="1"><widget class="QComboBox" name="comboVclMethod">
          <item><property name="text"><string>Linear</string></property></item>
          <item><property name="text"><string>Larionov Tertiary</string></property></item>
          <item><property name="text"><string>Larionov Older</string></property></item>
          <item><property name="text"><string>Clavier</string></property></item>
          <item><property name="text"><string>Steiber</string></property></item>
         </widget></item>
        </layout>
       </widget>
      </item>
      
      <item>
       <widget class="QGroupBox" name="groupVshOptions">
        <property name="title"><string>ADDITIONAL OPTIONS</string></property>
        <layout class="QGridLayout" name="gridVshOptions">
         <item row="0" column="0"><widget class="QCheckBox" name="checkVshShowCleanLine"><property name="text"><string>Show Sand Line (GR Clean)</string></property><property name="checked"><bool>true</bool></property></widget></item>
         <item row="0" column="1"><widget class="QCheckBox" name="checkVshShowShaleLine"><property name="text"><string>Show Shale Line (GR Shale)</string></property><property name="checked"><bool>true</bool></property></widget></item>
         <item row="1" column="0"><widget class="QCheckBox" name="checkVshHighlightHigh"><property name="text"><string>Highlight Shale (Vsh &gt; 0.5)</string></property><property name="checked"><bool>true</bool></property></widget></item>
         <item row="1" column="1"><widget class="QCheckBox" name="checkVshFlagHotShale"><property name="text"><string>Flag Hot Shale / Outliers</string></property><property name="checked"><bool>true</bool></property></widget></item>
         <item row="2" column="0"><widget class="QCheckBox" name="checkVshShowZones"><property name="text"><string>Show Zones</string></property></widget></item>
        </layout>
       </widget>
      </item>
      
      <item>
       <widget class="QGroupBox" name="groupVshActions">
        <property name="title"><string>ACTIONS</string></property>
        <layout class="QHBoxLayout" name="layoutVshActions">
         <item><widget class="QPushButton" name="btnCalcVsh"><property name="text"><string>Compute Vsh</string></property></widget></item>
         <item><widget class="QPushButton" name="btnVshModelComparison"><property name="text"><string>Compare All Models</string></property></widget></item>
         <item><widget class="QPushButton" name="btnUseVshWorkflow"><property name="text"><string>Apply to Interpretation</string></property></widget></item>
         <item><widget class="QPushButton" name="btnResetVsh"><property name="text"><string>Reset</string></property></widget></item>
        </layout>
       </widget>
      </item>
      
      <item>
       <widget class="QLabel" name="vshStatusLabel">
        <property name="styleSheet"><string>color: green;</string></property>
        <property name="text"><string /></property>
       </widget>
      </item>
      
      <!-- KPI CARDS -->
      <item>
       <widget class="QGroupBox" name="groupVshKPI">
        <property name="title"><string>RESULT SUMMARY</string></property>
        <layout class="QGridLayout" name="gridVshKPI">
         <item row="0" column="0">
          <widget class="QFrame" name="cardMeanVsh"><layout class="QVBoxLayout"><item><widget class="QLabel"><property name="text"><string>MEAN VSH</string></property></widget></item><item><widget class="QLabel" name="valMeanVsh"><property name="text"><string>--</string></property></widget></item></layout></widget>
         </item>
         <item row="0" column="1">
          <widget class="QFrame" name="cardNetSand"><layout class="QVBoxLayout"><item><widget class="QLabel"><property name="text"><string>NET SAND (VSH &lt;= 0.5)</string></property></widget></item><item><widget class="QLabel" name="valNetSand"><property name="text"><string>--</string></property></widget></item></layout></widget>
         </item>
         <item row="0" column="2">
          <widget class="QFrame" name="cardHighShale"><layout class="QVBoxLayout"><item><widget class="QLabel"><property name="text"><string>HIGH SHALE (VSH &gt; 0.5)</string></property></widget></item><item><widget class="QLabel" name="valHighShale"><property name="text"><string>--</string></property></widget></item></layout></widget>
         </item>
         <item row="1" column="0">
          <widget class="QFrame" name="cardVshRange"><layout class="QVBoxLayout"><item><widget class="QLabel"><property name="text"><string>VSH MIN - MAX</string></property></widget></item><item><widget class="QLabel" name="valVshRange"><property name="text"><string>--</string></property></widget></item></layout></widget>
         </item>
         <item row="1" column="1">
          <widget class="QFrame" name="cardMethodUsed"><layout class="QVBoxLayout"><item><widget class="QLabel"><property name="text"><string>METHOD USED</string></property></widget></item><item><widget class="QLabel" name="valMethodUsed"><property name="text"><string>--</string></property></widget></item></layout></widget>
         </item>
         <item row="1" column="2">
          <widget class="QFrame" name="cardConfidence"><layout class="QVBoxLayout"><item><widget class="QLabel"><property name="text"><string>CONFIDENCE</string></property></widget></item><item><widget class="QLabel" name="valConfidence"><property name="text"><string>--</string></property></widget></item></layout></widget>
         </item>
        </layout>
       </widget>
      </item>

      <item>
       <widget class="QGroupBox" name="groupVshZone">
        <property name="title"><string>ZONE CALCULATION</string></property>
        <layout class="QHBoxLayout">
         <item><widget class="QLabel"><property name="text"><string>From (m)</string></property></widget></item>
         <item><widget class="QDoubleSpinBox" name="spinZoneFrom"><property name="maximum"><double>99999.0</double></property></widget></item>
         <item><widget class="QLabel"><property name="text"><string>To (m)</string></property></widget></item>
         <item><widget class="QDoubleSpinBox" name="spinZoneTo"><property name="maximum"><double>99999.0</double></property></widget></item>
         <item><widget class="QPushButton" name="btnComputeZone"><property name="text"><string>Compute Zone</string></property></widget></item>
        </layout>
       </widget>
      </item>
      
      <item><spacer name="spacerVshLeftGroup"><property name="orientation"><enum>Qt::Vertical</enum></property></spacer></item>
     </layout>
    </item>

    <item>
     <!-- MIDDLE COLUMN -->
     <widget class="QGroupBox" name="groupVshTrack">
      <property name="title"><string>VSH TRACK VISUALIZATION</string></property>
      <layout class="QVBoxLayout">
       <item><widget class="QLabel" name="lblVshTrackInfo"><property name="text"><string /></property></widget></item>
       <item><widget class="QWidget" name="vshTrackCanvas" native="true"/></item>
      </layout>
     </widget>
    </item>

    <item>
     <!-- RIGHT COLUMN -->
     <layout class="QVBoxLayout" name="layoutVshRightColumn">
      <item>
       <widget class="QGroupBox" name="groupVshHist">
        <property name="title"><string>GAMMA RAY HISTOGRAM</string></property>
        <layout class="QVBoxLayout">
         <item>
          <layout class="QHBoxLayout">
           <item>
            <layout class="QVBoxLayout">
             <item><widget class="QLabel" name="lblGrP5"><property name="text"><string>P5: -- API</string></property></widget></item>
             <item><widget class="QLabel" name="lblGrP50"><property name="text"><string>P50: -- API</string></property></widget></item>
             <item><widget class="QLabel" name="lblGrP95"><property name="text"><string>P95: -- API</string></property></widget></item>
            </layout>
           </item>
           <item><spacer><property name="orientation"><enum>Qt::Horizontal</enum></property></spacer></item>
           <item><widget class="QPushButton" name="btnVshHistFullScreen"><property name="text"><string>Full Screen</string></property></widget></item>
          </layout>
         </item>
         <item><widget class="QWidget" name="vshHistCanvas" native="true" /></item>
        </layout>
       </widget>
      </item>
      
      <item>
       <widget class="QGroupBox" name="groupVshModelComp">
        <property name="title"><string>VSH MODEL COMPARISON</string></property>
        <layout class="QVBoxLayout">
         <item>
          <widget class="QTableWidget" name="tableVshComparison">
           <property name="columnCount"><number>6</number></property>
           <column><property name="text"><string>Depth (m)</string></property></column>
           <column><property name="text"><string>Linear</string></property></column>
           <column><property name="text"><string>Larionov Tertiary</string></property></column>
           <column><property name="text"><string>Larionov Older</string></property></column>
           <column><property name="text"><string>Clavier</string></property></column>
           <column><property name="text"><string>Steiber</string></property></column>
          </widget>
         </item>
        </layout>
       </widget>
      </item>
      
      <item>
       <widget class="QGroupBox" name="groupVshQuality">
        <property name="title"><string>DATA QUALITY &amp; WARNINGS</string></property>
        <property name="styleSheet"><string /></property>
        <layout class="QVBoxLayout">
         <item>
          <widget class="QFrame" name="frameHotShaleWarning">
           <property name="styleSheet"><string>background-color: #FFF3E0; border: 1px solid #FFAB91; border-radius: 5px;</string></property>
           <layout class="QHBoxLayout">
            <item><widget class="QLabel" name="lblHotShaleIcon"><property name="text"><string>⚠️</string></property></widget></item>
            <item>
             <layout class="QVBoxLayout">
              <item><widget class="QLabel"><property name="text"><string>Hot Shale Zone Detected</string></property><property name="styleSheet"><string>font-weight: bold; color: #D84315;</string></property></widget></item>
              <item><widget class="QLabel" name="lblHotShaleText"><property name="text"><string>High GR values (&gt; 190 API) found.</string></property></widget></item>
             </layout>
            </item>
           </layout>
          </widget>
         </item>
         <item>
          <widget class="QFrame" name="frameTipInfo">
           <property name="styleSheet"><string>background-color: #E3F2FD; border: 1px solid #90CAF9; border-radius: 5px;</string></property>
           <layout class="QHBoxLayout">
            <item><widget class="QLabel"><property name="text"><string>ℹ️</string></property></widget></item>
            <item><widget class="QLabel"><property name="text"><string>Tip: For consolidated formations, Larionov Older Rocks model often provides better results. Use 'Compare All Models' to evaluate.</string></property><property name="wordWrap"><bool>true</bool></property></widget></item>
           </layout>
          </widget>
         </item>
         <item><spacer><property name="orientation"><enum>Qt::Vertical</enum></property></spacer></item>
        </layout>
       </widget>
      </item>
     </layout>
    </item>

   </layout>
"""

new_elem = ET.fromstring(new_layout_xml)
tab_vsh.append(new_elem)

tree.write("ui/mainwindow.ui", xml_declaration=True, encoding="utf-8")
print("mainwindow.ui successfully updated with simplified VSH tab layout and 6-column comparison table!")

