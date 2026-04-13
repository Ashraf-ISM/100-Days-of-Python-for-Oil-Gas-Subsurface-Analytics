import sys
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QApplication, QTableWidgetItem
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5 import uic

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
UI_DIR = ROOT_DIR / "ui"
UI_FILE = "data_downloader.ui"

# ---------------------------------------------------------------------------
# RAW_DATA schema per row:
# (Name, Organization, Format, Coverage, Access Type, URL, Description)
# ---------------------------------------------------------------------------

RAW_DATA = {

    # -----------------------------------------------------------------------
    # SEISMIC DATA
    # -----------------------------------------------------------------------
    "tableSeismic": [
        (
            "Equinor Volve Data Village",
            "Equinor",
            "SEGY / ZGY / LAS",
            "Norway - North Sea",
            "Free / Open Access",
            "https://www.equinor.com/energy/volve-data-sharing",
            "A complete open dataset from the Volve field including 3D seismic (SEGY/ZGY), well logs, petrophysical evaluations, production data, and reports. One of the most complete open petroleum datasets available."
        ),
        (
            "Parihaka-3D Seismic Data",
            "NZPAM / Crown Minerals",
            "SEGY",
            "New Zealand - Taranaki Basin",
            "Free / Open Access",
            "https://data.nzpam.govt.nz/",
            "Open 3D seismic survey data from the Taranaki Basin available via New Zealand Petroleum and Minerals (NZPAM) online database. Includes interpretation and well tie data."
        ),
        (
            "SEAM Phase 1 – Collaboration Model",
            "SEG Advanced Modeling Corp.",
            "SEGY",
            "Synthetic – Deepwater Gulf of Mexico",
            "Paid / Licensed",
            "https://seg.org/Education/Research-and-data/SEAM",
            "SEG Advanced Modeling Corporation Phase 1 synthetic seismic dataset for imaging and inversion challenges. Complex geology including salt bodies and subsalt targets."
        ),
        (
            "Open Seismic Repository (OSR)",
            "SEG / Community",
            "SEGY",
            "Multiple Regions",
            "Free / Open Access",
            "https://wiki.seg.org/wiki/Open_data",
            "SEG Wiki aggregator listing all open seismic datasets globally. Includes Penobscot, F3 Netherlands, Stratton, Teapot Dome, and more with direct download links."
        ),
        (
            "F3 Netherlands Open Seismic",
            "dGB Earth Sciences",
            "SEGY / OpendTect",
            "Netherlands - North Sea",
            "Free / Open Access",
            "https://terranubis.com/datainfo/F3-Demo-2020",
            "Classic benchmark 3D seismic dataset from the F3 block, Dutch North Sea. Widely used in seismic interpretation training, machine learning, and algorithm benchmarking."
        ),
        (
            "Penobscot 3D Seismic & Wells",
            "dGB Earth Sciences / SEG",
            "SEGY / LAS",
            "Canada - Nova Scotia",
            "Free / Open Access",
            "https://terranubis.com/datainfo/Penobscot",
            "Open 3D seismic cube with multiple well logs for the Penobscot field, offshore Nova Scotia. Includes horizon interpretations and formation tops."
        ),
        (
            "Stratton Field Dataset",
            "UTIG / BEG",
            "SEGY / LAS",
            "Texas, USA - Onshore",
            "Free / Open Access",
            "https://wiki.seg.org/wiki/Stratton_3D_survey",
            "3D seismic survey from the Stratton field onshore Texas. Well documented with full well log suite. Often used for AVO and attribute analysis research."
        ),
        (
            "Teapot Dome 3D Seismic Survey",
            "RMOTC / DOE",
            "SEGY / LAS",
            "Wyoming, USA",
            "Free / Open Access",
            "https://wiki.seg.org/wiki/Teapot_Dome_3D_survey",
            "Full 3D seismic dataset from Rocky Mountain Oil Technology Center (RMOTC), Teapot Dome, Wyoming. Includes well logs, core, and production data. Excellent onshore training dataset."
        ),
        (
            "Poseidon 3D Seismic (NWS Australia)",
            "Geoscience Australia / NOPIMS",
            "SEGY",
            "Australia - NW Shelf",
            "Free / Open Access",
            "https://nopims.dmp.wa.gov.au/nopims/",
            "Multiple 3D seismic surveys from the North West Shelf, Australia. Available through NOPIMS portal as open-release data after embargo period."
        ),
        (
            "USGS National Seismic Hazard Data",
            "USGS",
            "SEGY / ASCII",
            "USA - National",
            "Free / Open Access",
            "https://earthquake.usgs.gov/hazards/hazmaps/",
            "National Seismic Hazard Maps data including ground-motion models and seismic source characterization for the contiguous United States."
        ),
        (
            "IRIS FDSN Seismic Waveforms",
            "IRIS Consortium",
            "miniSEED / SAC",
            "Global",
            "Free / Open Access",
            "https://ds.iris.edu/ds/nodes/dmc/data/",
            "IRIS Data Management Center provides global seismological waveform data. Includes earthquake records, ambient noise, and controlled-source data from thousands of stations worldwide."
        ),
        (
            "GeoNet New Zealand Seismograph",
            "GNS Science",
            "miniSEED",
            "New Zealand",
            "Free / Open Access",
            "https://www.geonet.org.nz/data/",
            "Real-time and archived seismograph data from New Zealand's national monitoring network. Includes earthquake catalogs, waveforms, and strong-motion records."
        ),
        (
            "OpendTect Open Seismic Datasets",
            "dGB Earth Sciences",
            "OpendTect / SEGY",
            "Multiple Regions",
            "Free (Registration)",
            "https://terranubis.com/",
            "TerraHub by dGB offers curated open datasets (F3, Penobscot, Groningen, etc.) optimized for use in OpendTect seismic interpretation software."
        ),
        (
            "CRUST1.0 Global Seismic Model",
            "UCSD / Scripps",
            "ASCII / NetCDF",
            "Global",
            "Free / Open Access",
            "https://igppweb.ucsd.edu/~gabi/crust1.html",
            "Global 1x1 degree model of Earth's crust including seismic velocities (Vp, Vs), density, and layer thicknesses from surface to Moho."
        ),
    ],

    # -----------------------------------------------------------------------
    # WELL LOG DATA
    # -----------------------------------------------------------------------
    "tableWellLog": [
        (
            "NLOG – Dutch Oil & Gas Portal",
            "TNO / Netherlands Enterprise Agency",
            "LAS / DLIS / LIS / PDF",
            "Netherlands",
            "Free / Open Access",
            "https://www.nlog.nl/en",
            "Public portal for the Netherlands with well logs, seismic surveys, well reports, production data, and field maps. Covers onshore and offshore Dutch sector."
        ),
        (
            "Norwegian Petroleum Directorate (NPD) Diskos",
            "Norwegian Offshore Directorate (NOD)",
            "LAS / DLIS / WITSML",
            "Norway – NCS",
            "Free / Open Access",
            "https://www.sodir.no/en/data-and-services/",
            "Extensive open data spanning the Norwegian Continental Shelf: wellbores, field data, seismic surveys, production, and facilities. Includes Diskos National Data Repository."
        ),
        (
            "KGS Well Log Database",
            "Kansas Geological Survey",
            "LAS / DLIS",
            "Kansas, USA",
            "Free / Open Access",
            "https://www.kgs.ku.edu/Magellan/Logs/index.html",
            "Huge database of wireline logs for the state of Kansas with over 120,000 wells. Includes gamma ray, resistivity, neutron, density, and sonic logs in LAS format."
        ),
        (
            "NOPIMS – National Offshore Petroleum",
            "Geoscience Australia / DMIRS WA",
            "LAS / DLIS / PDF / SEGY",
            "Australia – Offshore",
            "Free / Open Access",
            "https://nopims.dmp.wa.gov.au/nopims/",
            "National Offshore Petroleum Information Management System. Vast repository of Australian offshore well logs, seismic, cores, reports, and production data."
        ),
        (
            "UK NDR – National Data Repository",
            "NSTA (North Sea Transition Authority)",
            "LAS / DLIS / LIS / PDF",
            "UK – North Sea",
            "Free / Open Access",
            "https://ndr.nstauthority.co.uk/",
            "Central repository for UK offshore petroleum data. Wellbores, wire-line logs, well reports, seismic, and core data from the entire UK continental shelf."
        ),
        (
            "TGS Open Data Well Logs",
            "TGS",
            "LAS / DLIS",
            "Gulf of Mexico, USA",
            "Free (Selected)",
            "https://www.tgs.com/data-products",
            "Selected open well log datasets from Gulf of Mexico. TGS also maintains commercial databases for global well data. Contact for specific open releases."
        ),
        (
            "OGA / NSTA National Well Data",
            "NSTA UK",
            "LAS / WITSML / CSV",
            "UK – North Sea",
            "Free / Open Access",
            "https://www.nstauthority.co.uk/data-centre/",
            "UK Offshore Petroleum Regulator data centre including wellbore trajectory, tops, completion reports, and petrophysical data open for download."
        ),
        (
            "New Zealand Petroleum Wells (NZPAM)",
            "Crown Minerals – New Zealand",
            "LAS / DLIS / PDF",
            "New Zealand",
            "Free / Open Access",
            "https://data.nzpam.govt.nz/",
            "Full well data archive for New Zealand petroleum wells including wireline logs, completion reports, drill cuttings, and core analysis data."
        ),
        (
            "USGS National Water Information (NWIS)",
            "USGS",
            "LAS / CSV / JSON",
            "USA – National",
            "Free / Open Access",
            "https://waterdata.usgs.gov/nwis",
            "Well and borehole data including water level measurements, lithology logs, and formation water chemistry from over 1.5 million monitoring sites across the USA."
        ),
        (
            "Geoscience Australia Well Data",
            "Geoscience Australia",
            "LAS / DLIS / CSV",
            "Australia – Onshore & Offshore",
            "Free / Open Access",
            "https://www.ga.gov.au/data-pubs/",
            "Geoscience Australia's data portal with onshore and offshore well data, stratigraphic drillholes, and mineral exploration boreholes across Australia."
        ),
        (
            "EIA US Well Completion Reports",
            "U.S. Energy Information Administration",
            "Excel / CSV",
            "USA – National",
            "Free / Open Access",
            "https://www.eia.gov/petroleum/drilling/",
            "US domestic well completion and drilling productivity reports. Includes active rig counts, new well production, and legacy well performance data."
        ),
        (
            "NERC BGS Borehole Records",
            "British Geological Survey (BGS)",
            "LAS / PDF / AGS",
            "UK – Onshore",
            "Free / Open Access",
            "https://www.bgs.ac.uk/geological-data/national-geoscience-data-centre/",
            "National Geoscience Data Centre borehole records from onshore UK. Includes engineering, mineral exploration, geothermal, and hydrocarbon boreholes."
        ),
        (
            "IRIS MUSTANG Well Log Archive",
            "IRIS / GSN",
            "LAS / DLIS",
            "Global",
            "Free / Open Access",
            "https://ds.iris.edu/mda/",
            "IRIS Metadata Aggregator includes borehole seismometer and ANSS borehole data. Useful for calibrating VSP and sonic log data against surface seismics."
        ),
        (
            "Schlumberger / SLB Open Well Data",
            "SLB (Schlumberger)",
            "LAS / CSV",
            "Various",
            "Free (Selected)",
            "https://www.slb.com/resource-library",
            "SLB occasionally releases open well log and petrophysical datasets for research and algorithm testing. Check their resource library for open data packages."
        ),
    ],

    # -----------------------------------------------------------------------
    # GEOLOGICAL & GEOSPATIAL DATA
    # -----------------------------------------------------------------------
    "tableGeo": [
        (
            "USGS EarthExplorer",
            "USGS",
            "Shapefiles / GeoTIFF / DEM / HDF",
            "Global",
            "Free / Open Access",
            "https://earthexplorer.usgs.gov/",
            "Comprehensive USGS repository for Earth science data including satellite imagery, DEMs, aerial photography, and topographic maps. Supports data filtering by area of interest."
        ),
        (
            "OneGeology Portal",
            "OneGeology Initiative",
            "WMS / WFS / GeoPackage",
            "Global",
            "Free / Open Access",
            "http://www.onegeology.org/",
            "International initiative providing geological map data globally at 1:1,000,000 scale. Covers bedrock geology, lithology, age, and structural features from national surveys."
        ),
        (
            "USGS National Geologic Map Database",
            "USGS",
            "Shapefiles / GeoPDF / ESRI",
            "USA",
            "Free / Open Access",
            "https://ngmdb.usgs.gov/",
            "Portal for US geological maps from state surveys and USGS. Includes bedrock, surficial, and geologic hazard maps at multiple scales."
        ),
        (
            "GEBCO Global Bathymetry",
            "GEBCO / BODC",
            "NetCDF / GeoTIFF / ASCII",
            "Global – Ocean",
            "Free / Open Access",
            "https://www.gebco.net/data_and_products/gridded_bathymetry_data/",
            "General Bathymetric Chart of the Oceans (GEBCO) provides the most authoritative global seafloor topography grid at 15 arc-second resolution."
        ),
        (
            "SRTM / ASTER Global DEMs",
            "NASA / METI",
            "GeoTIFF / HGT",
            "Global",
            "Free / Open Access",
            "https://earthdata.nasa.gov/",
            "SRTM 30m and ASTER GDEM 30m global digital elevation models. Essential base data for geological mapping, basin analysis, and geohazard assessment."
        ),
        (
            "OpenStreetMap Geological Features",
            "OpenStreetMap Foundation",
            "OSM / Shapefiles / GeoJSON",
            "Global",
            "Free / Open License",
            "https://www.openstreetmap.org/",
            "Open community-sourced map with geological and geotechnical features. Download extracts from Geofabrik or use Overpass API to query specific geological data."
        ),
        (
            "Copernicus Land Monitoring Service",
            "ESA / EEA",
            "GeoTIFF / Shapefiles / WMS",
            "Europe + Global",
            "Free / Open Access",
            "https://land.copernicus.eu/",
            "European land cover, land use, and topographic data. Includes CORINE Land Cover, Digital Elevation Models, and Urban Atlas at high resolution."
        ),
        (
            "BGS Digital Geological Maps UK",
            "British Geological Survey",
            "Shapefiles / GeoPackage / WMS",
            "UK",
            "Mixed (Some Free)",
            "https://www.bgs.ac.uk/geological-data/",
            "BGS DiGMap: digital geological maps of the UK at 1:625k and 1:50k scale. Bedrock and superficial geology, fault data, and hydrogeology layers."
        ),
        (
            "Geoscience Australia National Map",
            "Geoscience Australia",
            "Shapefiles / GeoTIFF / WMS",
            "Australia",
            "Free / Open Access",
            "https://www.ga.gov.au/data-pubs/",
            "Comprehensive Australian geoscience data including geology, geophysics, topography, and marine data. Access via the nationalmap.gov.au interactive portal."
        ),
        (
            "Global Lithological Map (GLiM)",
            "University of Hamburg",
            "Shapefiles / ASCII",
            "Global",
            "Free / Open Access",
            "https://www.geo.uni-hamburg.de/en/geologie/forschung/aquifer.html",
            "Global Lithological Map with 16 lithological classes covering the Earth's surface. Useful for regional geological and hydrogeological analysis."
        ),
        (
            "PANGAEA Geoscience Data Publisher",
            "PANGAEA / MARUM",
            "NetCDF / CSV / XLS / Various",
            "Global – Marine & Terrestrial",
            "Free / Open Access",
            "https://www.pangaea.de/",
            "Open access library and data publisher for geological and environmental science. Hosts millions of datasets from marine sediment cores, boreholes, and field campaigns."
        ),
        (
            "NASA Earthdata Portal",
            "NASA",
            "HDF5 / NetCDF / GeoTIFF",
            "Global",
            "Free / Open Access",
            "https://earthdata.nasa.gov/",
            "Comprehensive NASA data portal with land, ocean, atmosphere, and cryosphere datasets. Includes MODIS, Landsat, ICESat, and GRACE satellite products."
        ),
    ],

    # -----------------------------------------------------------------------
    # GEOPHYSICAL DATA (Potential Fields, EM, VSP, etc.)
    # -----------------------------------------------------------------------
    "tableGeophysical": [
        (
            "NOAA NCEI Marine Gravity & Magnetics",
            "NOAA / NCEI",
            "ASCII / NetCDF / Grids",
            "Global – Marine",
            "Free / Open Access",
            "https://www.ncei.noaa.gov/products/marine-magnetics-gravity",
            "Marine magnetic and gravity data from decades of ship-track surveys. Includes satellite-derived gravity anomaly grids (Sandwell & Smith) and magnetic anomaly grids."
        ),
        (
            "World Magnetic Model (WMM)",
            "NOAA / BGS",
            "ASCII / API",
            "Global",
            "Free / Open Access",
            "https://www.ngdc.noaa.gov/geomag/WMM/",
            "The standard geomagnetic reference field model updated every 5 years. Provides declination, inclination, and total field intensity globally. Essential for magnetic survey corrections."
        ),
        (
            "Australian National Gravity Database",
            "Geoscience Australia",
            "ASCII / CSV / GeoTIFF",
            "Australia",
            "Free / Open Access",
            "https://www.ga.gov.au/scientific-topics/earth-obs/geodesy/gravity",
            "Over 1.5 million onshore Bouguer and Free Air gravity observations across Australia. Includes national grids and station point data."
        ),
        (
            "BGS UK Gravity & Magnetic Surveys",
            "British Geological Survey",
            "ASCII / GeoTIFF / Shapefiles",
            "UK",
            "Mixed (Some Free)",
            "https://www.bgs.ac.uk/datasets/",
            "UK national gravity and magnetic anomaly datasets including the UK Bouguer anomaly grid and total field magnetic anomaly grids at 200m resolution."
        ),
        (
            "EMAG2 – Earth Magnetic Anomaly Grid",
            "NOAA / CIRES",
            "NetCDF / GeoTIFF / ASCII",
            "Global",
            "Free / Open Access",
            "https://www.ngdc.noaa.gov/geomag/emag2.html",
            "Global 2 arc-minute resolution magnetic anomaly grid compiled from satellite, marine, aeromagnetic, and ground-based observations. V3 has improved resolution and reduced noise."
        ),
        (
            "WDMAM – World Digital Magnetic Anomaly",
            "IAGA / CCGM",
            "GeoTIFF / ASCII",
            "Global",
            "Free / Open Access",
            "https://www.wdmam.org/",
            "World Digital Magnetic Anomaly Map compiled from aeromagnetic and marine magnetic surveys. Released under the auspices of IAGA and UNESCO. 3 arc-minute resolution."
        ),
        (
            "Global Gravity Field Models (GOCE / GRACE)",
            "ESA / GFZ Potsdam",
            "ICGEM / NetCDF / Shapefiles",
            "Global",
            "Free / Open Access",
            "https://icgem.gfz-potsdam.de/",
            "International Centre for Global Earth Models. Access spherical harmonic gravity field models including EIGEN-6C4, EGM2008, and GOCE-derived models for isostasy and basin analysis."
        ),
        (
            "IRIS PASSCAL MT & EM Archive",
            "IRIS / PASSCAL",
            "EDI / ASCII",
            "Global",
            "Free / Open Access",
            "https://ds.iris.edu/ds/nodes/passcal/",
            "IRIS PASSCAL archive includes magnetotelluric (MT) and controlled-source EM field data from academic surveys globally. Useful for deep crustal resistivity studies."
        ),
        (
            "EGM2008 Global Gravity Model",
            "NGA (USA)",
            "ASCII / Binary",
            "Global",
            "Free / Open Access",
            "https://earth-info.nga.mil/",
            "Earth Gravitational Model 2008 – global 2.5 arc-minute spherical harmonic model. Standard reference for exploration gravity surveys worldwide."
        ),
        (
            "NASA GRACE Terrestrial Water Storage",
            "NASA / JPL",
            "NetCDF / ASCII",
            "Global",
            "Free / Open Access",
            "https://grace.jpl.nasa.gov/data/",
            "GRACE and GRACE-FO time-variable gravity data tracking terrestrial water storage changes. Used in basin hydrology, aquifer depletion studies, and isostatic rebound research."
        ),
    ],

    # -----------------------------------------------------------------------
    # SATELLITE & REMOTE SENSING DATA
    # -----------------------------------------------------------------------
    "tableSatellite": [
        (
            "Copernicus Open Access Hub (Sentinel)",
            "ESA",
            "SAFE / GeoTIFF / NetCDF",
            "Global",
            "Free / Open Access",
            "https://browser.dataspace.copernicus.eu/",
            "Sentinel-1 (SAR), Sentinel-2 (Multispectral), Sentinel-3 (Ocean/Land), and Sentinel-5P (Atmosphere) satellite data. Essential for surface geology, lineament mapping, and vegetation analysis."
        ),
        (
            "USGS Landsat Archive (EarthExplorer)",
            "USGS / NASA",
            "GeoTIFF / HDF",
            "Global",
            "Free / Open Access",
            "https://earthexplorer.usgs.gov/",
            "Complete Landsat 1–9 archive (1972 to present). Multi-spectral data at 15–30m resolution. Invaluable for alteration mapping, geological lineaments, and lithological discrimination."
        ),
        (
            "NASA ASTER Thermal & SWIR Data",
            "NASA / METI / Japan",
            "HDF-EOS / GeoTIFF",
            "Global",
            "Free / Open Access",
            "https://asterweb.jpl.nasa.gov/",
            "ASTER instrument on Terra satellite: VNIR, SWIR (thermal), and TIR bands at 15–90m. Exceptional for mineral mapping (iron oxides, clay minerals, carbonates) and surface temperature."
        ),
        (
            "NASA MODIS Land & Ocean Products",
            "NASA LAADS DAAC",
            "HDF / NetCDF / GeoTIFF",
            "Global",
            "Free / Open Access",
            "https://ladsweb.modaps.eosdis.nasa.gov/",
            "Moderate Resolution Imaging Spectroradiometer data from Terra and Aqua satellites. Global 250m–1km resolution, 36 spectral bands. Daily to monthly composites for land surface analysis."
        ),
        (
            "Planet Labs Open Imagery",
            "Planet Labs",
            "GeoTIFF",
            "Global",
            "Education / Research",
            "https://www.planet.com/nicfi/",
            "Planet NICFI (Norway) program provides free monthly 4.77m Basemaps for tropical regions. High-cadence 3m–5m PlanetScope and 72cm SkySat commercial imagery also available."
        ),
        (
            "Google Earth Engine Data Catalog",
            "Google",
            "EE Image / Raster / Vector",
            "Global",
            "Free / Requires Account",
            "https://developers.google.com/earth-engine/datasets",
            "Petabyte-scale geospatial analysis platform with hundreds of public datasets including Landsat, Sentinel, MODIS, DEMs, and climate data. Processing performed in the cloud."
        ),
        (
            "Sentinel Hub EO Browser",
            "Sinergise / ESA",
            "GeoTIFF / JPEG2000",
            "Global",
            "Free (Tier Limited)",
            "https://apps.sentinel-hub.com/eo-browser/",
            "Online browsing and download portal for Sentinel-1, 2, 3, 5P plus Landsat and other optical data with band math visualization. Developer API available for bulk access."
        ),
        (
            "JAXA ALOS / PALSAR Archive",
            "JAXA",
            "GeoTIFF / CEOS",
            "Global",
            "Free (Registration)",
            "https://www.eorc.jaxa.jp/ALOS/en/index_e.htm",
            "JAXA ALOS-1 and ALOS-2 PALSAR L-band SAR data for geological mapping, surface deformation (InSAR), and forest monitoring. Excellent for structural geology and fault mapping."
        ),
        (
            "INSAR & DEM via ASF / UNAVCO",
            "ASF / UNAVCO",
            "GeoTIFF / NetCDF / CEOS",
            "Global",
            "Free / Open Access",
            "https://search.asf.alaska.edu/",
            "Alaska Satellite Facility provides Sentinel-1, ALOS PALSAR, and ERS InSAR data. Ideal for surface deformation, landslide monitoring, and subsidence mapping over oil/gas fields."
        ),
        (
            "NOAA AVHRR Polar Orbiter Data",
            "NOAA",
            "HDF / NetCDF",
            "Global",
            "Free / Open Access",
            "https://www.ncei.noaa.gov/products/avhrr",
            "Advanced Very High Resolution Radiometer (AVHRR) archive spanning 1979 to present. Thermal infrared for sea surface temperature, volcanic thermal anomalies, and land surface."
        ),
        (
            "NASA ICESat-2 Elevation Data",
            "NASA",
            "HDF5 / ATL products",
            "Global",
            "Free / Open Access",
            "https://icesat-2.gsfc.nasa.gov/data",
            "ICESat-2 photon-counting lidar data with sub-meter vertical accuracy. Used for ice sheet mass balance, forest canopy height, inland water levels, and bathymetry."
        ),
    ],

    # -----------------------------------------------------------------------
    # PETROPHYSICAL & CORE DATA
    # -----------------------------------------------------------------------
    "tablePetro": [
        (
            "Digital Rocks Portal (UT Austin)",
            "University of Texas at Austin",
            "TIFF / HDF5 / STL / RAW",
            "Global – Synthetic & Real Core",
            "Free / Open Access",
            "https://www.digitalrocksportal.org/",
            "Open repository for pore-scale micro-CT images and digital rock physics datasets. Includes carbonate, sandstone, shale, and tight rock samples with porosities and permeabilities."
        ),
        (
            "NLOG Core Sample Database",
            "TNO Netherlands",
            "PDF / LAS / CSV",
            "Netherlands",
            "Free / Open Access",
            "https://www.nlog.nl/en/core",
            "Core sample analysis data from Dutch sector wells including routine core analysis (RCA), special core analysis (SCAL), and thin section descriptions."
        ),
        (
            "USGS Core Research Center (CRC)",
            "USGS",
            "PDF / CSV / Images",
            "USA",
            "Free / Open Access",
            "https://www.usgs.gov/centers/core-research-center",
            "World's largest repository of government-owned geological cores. Stores over 3 million meters of cores from oil, gas, and water wells across the United States."
        ),
        (
            "Brugge Field Benchmark Dataset",
            "TNO / SPE",
            "Eclipse / CSV / LAS",
            "Synthetic – Netherlands Based",
            "Free / Open Access",
            "https://www.spe.org/en/what-is-spe/research/datasets/",
            "SPE Brugge benchmark dataset for history matching and uncertainty quantification. Includes full reservoir model, well data, production history, and petrophysical properties."
        ),
        (
            "SCAL / MICP Open Datasets (GitHub)",
            "Community / Various",
            "CSV / Excel / LAS",
            "Various",
            "Free / Open Source",
            "https://github.com/yohanesnuwara/pyreservoir",
            "GitHub repository pyreservoir by Yohanes Nuwara. Includes SCAL data, relative permeability curves, capillary pressure (MICP), and petrophysical analysis notebooks."
        ),
        (
            "OpenPNM Pore Network Model Data",
            "PMEAL Group",
            "JSON / CSV / HDF5",
            "Synthetic",
            "Free / Open Source",
            "https://github.com/PMEAL/OpenPNM",
            "Open-source pore network modeling toolkit with bundled pore geometry datasets for sandstone and carbonate systems. Ideal for digital rock physics research."
        ),
        (
            "NIST Rock Physics Datasets",
            "NIST",
            "CSV / Excel",
            "USA",
            "Free / Open Access",
            "https://www.nist.gov/",
            "Standard rock physics datasets with measured elastic properties, porosity, permeability, and mineralogy for calibration of well log interpretation models."
        ),
    ],

    # -----------------------------------------------------------------------
    # PRODUCTION & RESERVOIR DATA
    # -----------------------------------------------------------------------
    "tableReservoir": [
        (
            "NPD FactPages – Norwegian Production",
            "Norwegian Offshore Directorate",
            "CSV / Excel / JSON",
            "Norway – NCS",
            "Free / Open Access",
            "https://www.factpages.sodir.no/en",
            "Official Norwegian production data including field production history, well production tests, injection volumes, reserves estimates, and facility information."
        ),
        (
            "UK NSTA Production Data",
            "NSTA UK",
            "CSV / Excel",
            "UK – North Sea",
            "Free / Open Access",
            "https://www.nstauthority.co.uk/data-centre/nsta-open-data/",
            "UK offshore oil and gas production data by field and well. Includes annual and monthly production volumes, operator details, and field cessation data."
        ),
        (
            "US EIA Production Statistics",
            "U.S. Energy Information Administration",
            "Excel / CSV / JSON API",
            "USA – National",
            "Free / Open Access",
            "https://www.eia.gov/petroleum/",
            "Comprehensive US petroleum production, reserves, imports, exports, and refinery data. Includes shale play production breakdowns and Drilling Productivity Reports."
        ),
        (
            "SPE OnePetro Benchmark Datasets",
            "SPE International",
            "Eclipse / CSV / LAS",
            "Various – Synthetic & Real",
            "Member / Some Free",
            "https://www.spe.org/en/what-is-spe/research/datasets/",
            "Society of Petroleum Engineers benchmark datasets including PUNQ-S3, Egg Model, Brugge Field, and Norne Field for reservoir simulation and history matching research."
        ),
        (
            "OPM ResInsight Open Reservoir Models",
            "OPM Initiative",
            "Eclipse / OPM Format",
            "Various – Synthetic",
            "Free / Open Source",
            "https://github.com/OPMgroup/opm-tests",
            "Open Porous Media (OPM) test cases and benchmark reservoir simulation models. Includes Norne, Brugge, and synthetic models for testing open-source simulation code."
        ),
        (
            "Norne Field Full Dataset (NTNU)",
            "NTNU / Equinor / OPM",
            "Eclipse / RESQML / LAS",
            "Norway – North Sea",
            "Free / Open Access",
            "https://github.com/OPMgroup/norne",
            "Complete production dataset from the Norne field including reservoir simulation model, well data, production history, and seismic. Benchmark for history matching and ML workflows."
        ),
        (
            "Volve Production & Reservoir Model",
            "Equinor",
            "Eclipse / LAS / SEGY / RESQML",
            "Norway – North Sea",
            "Free / Open Access",
            "https://www.equinor.com/energy/volve-data-sharing",
            "Full Volve field dataset including Eclipse simulation model, history-matched production, RFT/MDT pressure data, and PVT fluid samples. Complete lifecycle petroleum dataset."
        ),
    ],

    # -----------------------------------------------------------------------
    # POTENTIAL FIELDS (Separate table for detailed analysis)
    # -----------------------------------------------------------------------
    "tableGeophysical": [
        (
            "NOAA NCEI Marine Gravity & Magnetics",
            "NOAA / NCEI",
            "ASCII / NetCDF / Grids",
            "Global – Marine",
            "Free / Open Access",
            "https://www.ncei.noaa.gov/products/marine-magnetics-gravity",
            "Marine magnetic and gravity data from ship-track surveys. Includes Sandwell satellite-derived gravity anomaly grids (V32) and the World Magnetic Anomaly Map."
        ),
        (
            "EMAG2 – Earth Magnetic Anomaly Grid",
            "NOAA / CIRES",
            "NetCDF / GeoTIFF / ASCII",
            "Global",
            "Free / Open Access",
            "https://www.ngdc.noaa.gov/geomag/emag2.html",
            "Global 2 arc-minute magnetic anomaly grid (V3) compiled from satellite, ship-track, aeromagnetic, and ground surveys. Standard reference for crustal studies and basement mapping."
        ),
        (
            "WDMAM – World Digital Magnetic Anomaly",
            "IAGA / CCGM",
            "GeoTIFF / ASCII",
            "Global",
            "Free / Open Access",
            "https://www.wdmam.org/",
            "World Digital Magnetic Anomaly Map at 3 arc-minute resolution. Comprehensive compilation of aeromagnetic and marine magnetic surveys for regional tectonic interpretation."
        ),
        (
            "ICGEM Gravity Field Models",
            "GFZ Potsdam",
            "ICGEM / NetCDF",
            "Global",
            "Free / Open Access",
            "https://icgem.gfz-potsdam.de/",
            "International Centre for Global Earth Models. Repository of spherical harmonic gravity models including EGM2008, EIGEN-6C4, and GOCE-derived models for basin and isostasy studies."
        ),
        (
            "Australian National Gravity Database",
            "Geoscience Australia",
            "CSV / ASCII / GeoTIFF",
            "Australia",
            "Free / Open Access",
            "https://www.ga.gov.au/scientific-topics/earth-obs/geodesy/gravity",
            "Over 1.5 million Bouguer and Free Air gravity observations across Australia with complete Bouguer anomaly and isostatic residual grids."
        ),
        (
            "NASA GRACE Time-Variable Gravity",
            "NASA / JPL",
            "NetCDF / ASCII",
            "Global",
            "Free / Open Access",
            "https://grace.jpl.nasa.gov/data/",
            "GRACE and GRACE-FO mass change data tracking groundwater depletion, ice sheet changes, and mantle flow. Monthly gravity field changes expressed as equivalent water height."
        ),
        (
            "BGS UK Gravity & Magnetic Data",
            "British Geological Survey",
            "ASCII / GeoTIFF",
            "UK",
            "Mixed (Some Free)",
            "https://www.bgs.ac.uk/datasets/",
            "UK Bouguer anomaly grid and total field magnetic anomaly grids at 200m resolution. Includes offshore UK gravity and magnetic compilations from multi-client surveys."
        ),
        (
            "IRIS PASSCAL Magnetotelluric Archive",
            "IRIS / PASSCAL",
            "EDI / ASCII",
            "Global",
            "Free / Open Access",
            "https://ds.iris.edu/ds/nodes/passcal/",
            "Magnetotelluric (MT) and controlled-source EM (CSEM) field data from academic surveys. Used for deep crustal resistivity and salt body imaging."
        ),
    ],

    # -----------------------------------------------------------------------
    # MACHINE LEARNING & BENCHMARK DATASETS
    # -----------------------------------------------------------------------
    "tableML": [
        (
            "SEG Machine Learning Contest Datasets",
            "SEG",
            "CSV / LAS / SEGY / Numpy",
            "Various",
            "Free / Open Access",
            "https://github.com/seg/2016-ml-contest",
            "Multiple SEG ML competition datasets including the 2016 Facies Classification dataset (well logs → facies), 2019 seismic facies classification, and salt body detection challenges."
        ),
        (
            "TGS Salt Identification (Kaggle)",
            "TGS / Kaggle",
            "TIFF / CSV",
            "Gulf of Mexico (Synthetic)",
            "Free / Open Access",
            "https://www.kaggle.com/c/tgs-salt-identification-challenge",
            "Kaggle competition dataset with ~4,000 seismic images for semantic segmentation of salt body boundaries. Standard benchmark for U-Net and deep learning in seismic interpretation."
        ),
        (
            "Facies Classification (SEG 2016)",
            "SEG / Community",
            "CSV / LAS",
            "Kansas, USA",
            "Free / Open Access",
            "https://github.com/seg/2016-ml-contest",
            "Canonical ML well log facies classification dataset. 10 wells with 7 log curves and 9 geological facies labels. Baseline for supervised classification models in petrophysics."
        ),
        (
            "FORCE 2020 Well Log ML Challenge",
            "NPD / FORCE",
            "CSV / LAS",
            "Norway – NCS",
            "Free / Open Access",
            "https://github.com/bolgebrygg/force-2020-machine-learning-competition",
            "FORCE 2020 lithology and fluid prediction challenge. 98 training wells and 10 blind wells from the Norwegian Continental Shelf with 11 well log curves and lithology labels."
        ),
        (
            "Open ML Petrophysics (GitHub)",
            "Yohanes Nuwara",
            "CSV / LAS / Jupyter",
            "Various",
            "Free / Open Source",
            "https://github.com/yohanesnuwara/pyreservoir",
            "Open-source petrophysics Python notebooks with bundled LAS datasets. Includes porosity-permeability transforms, water saturation models, and NMR interpretation examples."
        ),
        (
            "GeoLatAI Datasets (Latin America ML)",
            "GeoLatAI Community",
            "CSV / LAS / Numpy",
            "Latin America",
            "Free / Open Access",
            "https://github.com/geolatai",
            "Community-driven collection of geoscience ML datasets focused on Latin American basins. Includes seismic attribute prediction and formation top picking challenges."
        ),
        (
            "Synthetic Seismic ML Benchmarks (DeepSeis)",
            "DeepSeis / Community",
            "SEGY / Numpy",
            "Synthetic",
            "Free / Open Source",
            "https://github.com/DeepSeis",
            "Synthetic seismic datasets generated from geological models for benchmarking deep learning algorithms in seismic interpretation, fault detection, and facies classification."
        ),
        (
            "Netherlands F3 Facies ML Dataset",
            "dGB / Community",
            "SEGY / CSV",
            "Netherlands – North Sea",
            "Free / Open Access",
            "https://github.com/olivesgatech/facies_classification",
            "Pre-processed F3 seismic dataset ready for deep learning facies classification. Annotated seismic inline sections with 6 geological facies. PyTorch / TensorFlow compatible."
        ),
        (
            "Zenodo Geoscience Open Data",
            "CERN / Zenodo",
            "Various",
            "Global",
            "Free / Open Access",
            "https://zenodo.org/search?q=geoscience+petroleum",
            "Open-access scientific repository hosting various geoscience ML datasets, petrophysical tables, seismic attributes, and geological model outputs from research publications."
        ),
    ],

    # -----------------------------------------------------------------------
    # OPEN-SOURCE TOOLS & GITHUB REPOSITORIES
    # -----------------------------------------------------------------------
    "tableTools": [
        (
            "OpendTect (dGB Earth Sciences)",
            "dGB Earth Sciences",
            "OpendTect / SEGY / LAS",
            "Cross-Platform",
            "Free (Community Edition)",
            "https://dgbes.com/software/opendtect/",
            "Open-source seismic interpretation platform. Community edition is fully functional with volume rendering, horizon picking, fault interpretation, and seismic attribute analysis."
        ),
        (
            "Madagascar Seismic Processing",
            "Madagascar Community",
            "RSFC (internal) / SEGY",
            "Cross-Platform",
            "Free / Open Source",
            "https://github.com/ahay/src",
            "Open-source geophysical data analysis and reproducible research framework. Includes processing modules for seismic migration, NMO, velocity analysis, and filtering."
        ),
        (
            "Bruges – Petrophysics Python Library",
            "Agile Scientific",
            "Python (pip)",
            "Cross-Platform",
            "Free / Open Source",
            "https://github.com/agile-geoscience/bruges",
            "Python library for seismic forward modeling, AVO analysis, rock physics transforms, and well log processing. Widely used in geoscience data science workflows."
        ),
        (
            "Lasio – LAS File Reader (Python)",
            "kinverarity",
            "Python (pip)",
            "Cross-Platform",
            "Free / Open Source",
            "https://github.com/kinverarity1/lasio",
            "Python library for reading and writing LAS (Log ASCII Standard) well log files. Supports LAS 1.2 and 2.0. Standard tool for petrophysical data workflows in Python."
        ),
        (
            "Welly – Well Log Object Library",
            "Agile Scientific",
            "Python (pip)",
            "Cross-Platform",
            "Free / Open Source",
            "https://github.com/agile-geoscience/welly",
            "Python library for working with well log data as objects. Built on top of lasio. Supports quality control, normalization, splicing, and visualisation of LAS data."
        ),
        (
            "ObsPy – Seismological Python Library",
            "ObsPy Community",
            "Python (pip)",
            "Cross-Platform",
            "Free / Open Source",
            "https://github.com/obspy/obspy",
            "Python framework for processing seismological data. Reads miniSEED, SEGY, SAC, and other formats. Connects to IRIS, GeoNet, and other FDSN data services directly."
        ),
        (
            "Segyio – SEGY File Library (Python)",
            "Equinor / SLB",
            "Python (pip)",
            "Cross-Platform",
            "Free / Open Source",
            "https://github.com/equinor/segyio",
            "Fast Python/C library for reading and writing SEG-Y seismic files. Supports random access, trace headers, and binary headers. Industry standard for Python seismic workflows."
        ),
        (
            "PyGEOS / Shapely Geospatial Tools",
            "Shapely Community",
            "Python (pip)",
            "Cross-Platform",
            "Free / Open Source",
            "https://github.com/shapely/shapely",
            "Python library for geometric operations on geological map data (polygons, lines, points). Used with geopandas for geological GIS analysis and map digitisation workflows."
        ),
        (
            "Fatiando a Terra – Geophysics Python",
            "Fatiando Community",
            "Python (pip)",
            "Cross-Platform",
            "Free / Open Source",
            "https://www.fatiando.org/",
            "Open-source geophysics Python package suite including Harmonica (potential fields), Boule (reference ellipsoids), Verde (gridding), and Pooch (data download management)."
        ),
        (
            "ResQML / OSDU Open Subsurface Stack",
            "Energistics / OSDU",
            "ResQML / WITSML / PRODML",
            "Cross-Platform",
            "Free (Spec Open)",
            "https://www.energistics.org/resqml-data-standards/",
            "Energistics data standards for subsurface data interchange. RESQML for reservoir models, WITSML for drilling, PRODML for production. Reference implementations available on GitHub."
        ),
    ],

    # -----------------------------------------------------------------------
    # RESEARCH & ACADEMIC DATA REPOSITORIE
    # -----------------------------------------------------------------------
    "tableResearch": [
        (
            "Zenodo Subsurface & Geoscience",
            "CERN / Zenodo",
            "Various (Linked to Publications)",
            "Global",
            "Free / Open Access",
            "https://zenodo.org/",
            "Open repository for scientific datasets, models, and software linked to journal publications. Covers petroleum, geophysics, remote sensing, and machine learning for geosciences."
        ),
        (
            "EarthChem Portal",
            "Lamont–Doherty / NSF",
            "CSV / Excel / XML",
            "Global",
            "Free / Open Access",
            "https://www.earthchem.org/",
            "Repository for geochemical, geochronological, and petrological data from igneous, metamorphic, and sedimentary rocks. Includes PetDB, NAVDAT, and SedDB databases."
        ),
        (
            "IODP/DSDP Ocean Drilling Data",
            "IODP / JRSO",
            "LAS / ASCII / CSV",
            "Global – Marine",
            "Free / Open Access",
            "https://www.iodp.org/data/",
            "International Ocean Discovery Program core and log data from ocean drilling expeditions. Hundreds of sites with complete stratigraphic, geochemical, and geophysical datasets."
        ),
        (
            "DRYAD Research Data Repository",
            "Dryad Digital Repository",
            "Various",
            "Global",
            "Free / Open Access",
            "https://datadryad.org/",
            "Open data repository for research publications. Increasingly used for geoscience datasets including well logs, outcrop measurements, and petrophysical lab data."
        ),
        (
            "Figshare Geoscience Datasets",
            "Figshare / Digital Science",
            "Various",
            "Global",
            "Free / Open Access",
            "https://figshare.com/",
            "Open research data repository with thousands of geoscience datasets. Includes supplementary data from Nature, Elsevier, and AGU journal publications."
        ),
        (
            "PANGAEA Geoscience Publisher",
            "AWI / MARUM Germany",
            "NetCDF / CSV / Various",
            "Global – Marine & Terrestrial",
            "Free / Open Access",
            "https://www.pangaea.de/",
            "Data library and publisher for earth and environmental science. Hosts millions of datasets from marine expeditions, boreholes, and environmental monitoring campaigns."
        ),
        (
            "British Library EThOS Geoscience",
            "British Library",
            "PDF / Shapefiles",
            "UK",
            "Free / Open Access",
            "https://ethos.bl.uk/",
            "Electronic Theses Online database. Geoscience PhD theses often contain novel datasets on UK geological formations, petrophysics, and basin analysis."
        ),
        (
            "AGU GeoSpace Data Center",
            "American Geophysical Union",
            "Various",
            "Global",
            "Free / Open Access",
            "https://agupubs.onlinelibrary.wiley.com/",
            "AGU journal data supplements including JGR Solid Earth, Geophysical Research Letters, and Tectonics. All data linked to publications available for open download."
        ),
    ],
}


class DataDownloaderWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        ui_path = UI_DIR / UI_FILE
        uic.loadUi(str(ui_path), self)

        self.current_url = ""
        self._populate_tables()
        self._connect_signals()

    def _populate_tables(self):
        for table_name, data in RAW_DATA.items():
            table = getattr(self, table_name, None)
            if not table:
                continue

            table.setRowCount(0)
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels([
                "Resource Name", "Organization", "Data Format",
                "Coverage", "Access Type", "URL"
            ])
            table.horizontalHeader().setStretchLastSection(True)

            for row_idx, row_data in enumerate(data):
                table.insertRow(row_idx)
                for col_idx in range(6):
                    item = QTableWidgetItem(row_data[col_idx])
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    if col_idx == 0:
                        item.setData(Qt.UserRole, row_data[6])
                    table.setItem(row_idx, col_idx, item)

            table.resizeColumnsToContents()
            table.itemSelectionChanged.connect(
                lambda t=table: self._on_table_selection_changed(t)
            )

    def _connect_signals(self):
        if hasattr(self, 'btnOpenBrowser'):
            self.btnOpenBrowser.clicked.connect(self._open_url)
        if hasattr(self, 'btnOpenInBrowserDetail'):
            self.btnOpenInBrowserDetail.clicked.connect(self._open_url)
        if hasattr(self, 'btnCopyLink'):
            self.btnCopyLink.clicked.connect(self._copy_link)
        if hasattr(self, 'btnCopyLinkDetail'):
            self.btnCopyLinkDetail.clicked.connect(self._copy_link)
        if hasattr(self, 'actionClose'):
            self.actionClose.triggered.connect(self.close)

    def _on_table_selection_changed(self, table):
        selected_items = table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        name = table.item(row, 0).text()
        desc = table.item(row, 0).data(Qt.UserRole)
        org  = table.item(row, 1).text()
        fmt  = table.item(row, 2).text()
        cov  = table.item(row, 3).text()
        acc  = table.item(row, 4).text()
        url  = table.item(row, 5).text()

        self.current_url = url

        if hasattr(self, 'lbl_name_val'):     self.lbl_name_val.setText(name)
        if hasattr(self, 'lbl_org_val'):      self.lbl_org_val.setText(org)
        if hasattr(self, 'lbl_format_val'):   self.lbl_format_val.setText(fmt)
        if hasattr(self, 'lbl_coverage_val'): self.lbl_coverage_val.setText(cov)
        if hasattr(self, 'lbl_access_val'):   self.lbl_access_val.setText(acc)
        if hasattr(self, 'urlLineEdit'):      self.urlLineEdit.setText(url)
        if hasattr(self, 'detailTextEdit'):   self.detailTextEdit.setPlainText(desc)

    def _open_url(self):
        if self.current_url:
            QDesktopServices.openUrl(QUrl(self.current_url))

    def _copy_link(self):
        if self.current_url:
            cb = QApplication.clipboard()
            cb.setText(self.current_url)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = DataDownloaderWindow()
    win.show()
    sys.exit(app.exec_())