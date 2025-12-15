import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import box, Point
import matplotlib.pyplot as plt
import folium
import rasterio
from branca.colormap import LinearColormap
import branca.colormap as cm
from pyproj import Transformer

# 시설 이름 한글화
facility_names = {
    "streetlight": "가로등",
    "senior_leisure": "노인여가복지시설",
    "senior_job": "노인일자리지원기관",
    "senior_homecare": "재가노인복지시설",
    "cctv": "CCTV",
    "intersection": "교차로",
    "bus_stop": "버스정류소",
    "hospital": "병의원",
    "market": "전통시장",
    "subway": "지하철역",
    "crosswalk": "횡단보도",
    "led_crosswalk": "LED 횡단보도",
    "walking_light": "보행등",
    "vehicle_entrance": "차량출입구",
    "traffic_camera": "단속카메라"
}

# 위험도 ASC 파일 불러오기
asc_path = "재현이 실수해서 다시한거/accident_avg.asc"
with rasterio.open(asc_path) as src:
    accident_data = src.read(1)
    transform = src.transform

transformer = Transformer.from_crs("EPSG:5186", "EPSG:4326", always_xy=True)

rows, cols = accident_data.shape
cell_polygons = []
values = []

for row in range(rows):
    for col in range(cols):
        value = accident_data[row, col]
        if value <= 0:
            continue
        x1, y1 = transform * (col, row)
        x2, y2 = transform * (col + 1, row + 1)
        lon1, lat1 = transformer.transform(x1, y1)
        lon2, lat2 = transformer.transform(x2, y2)
        cell = box(lon1, lat2, lon2, lat1)
        cell_polygons.append(cell)
        values.append(value)

accident_gdf = gpd.GeoDataFrame({'value': values, 'geometry': cell_polygons}, crs="EPSG:4326")

# 동대문구 shp 파일 불러오기
shp_path = "데이터/sig_20230729/sig.shp"
gdf = gpd.read_file(shp_path)
dongdaemun = gdf[gdf["SIG_ENG_NM"] == "Dongdaemun-gu"]
if dongdaemun.crs is None:
    dongdaemun = dongdaemun.set_crs(epsg=5179)
dongdaemun = dongdaemun.to_crs(epsg=4326)  # WGS84로 변환

# 노인보호구역 데이터 불러오기
protection_data = pd.read_csv("데이터/서울특별시_동대문구_노인장애인보호구역_20240806.csv")

# 동대문구 경계 좌표 가져오기
bounds = dongdaemun.total_bounds  # [minx, miny, maxx, maxy]
dongdaemun_bounds = {
    'min_lon': bounds[0],  # 최소 경도
    'max_lon': bounds[2],  # 최대 경도
    'min_lat': bounds[1],  # 최소 위도
    'max_lat': bounds[3]   # 최대 위도
}

# 30x30 격자 생성
def create_grid(bounds, n_rows=30, n_cols=30):
    lon_step = (bounds['max_lon'] - bounds['min_lon']) / n_cols
    lat_step = (bounds['max_lat'] - bounds['min_lat']) / n_rows
    
    grid_cells = []
    for i in range(n_rows):
        for j in range(n_cols):
            min_lon = bounds['min_lon'] + j * lon_step
            max_lon = min_lon + lon_step
            min_lat = bounds['min_lat'] + i * lat_step
            max_lat = min_lat + lat_step
            
            cell = box(min_lon, min_lat, max_lon, max_lat)
            grid_cells.append({
                'cell_id': f'{i}_{j}',
                'geometry': cell,
                'row': i,
                'col': j
            })
    
    return gpd.GeoDataFrame(grid_cells, crs="EPSG:4326")

# 시설 데이터를 격자에 매핑하는 함수
def count_facilities_in_grid(facilities_df, grid_gdf, lon_col, lat_col):
    counts = np.zeros(len(grid_gdf))
    
    # 시설 데이터를 GeoDataFrame으로 변환
    facilities_gdf = gpd.GeoDataFrame(
        facilities_df,
        geometry=[Point(xy) for xy in zip(facilities_df[lon_col], facilities_df[lat_col])],
        crs="EPSG:4326"
    )
    
    for idx, facility in facilities_gdf.iterrows():
        for i, grid_cell in grid_gdf.iterrows():
            if grid_cell.geometry.contains(facility.geometry):
                counts[i] += 1
                break
    
    return counts

# 파일 경로들 정리
file_paths = {
    "streetlight": "데이터/동대문구 가로등 위치 정보.csv",
    "senior_leisure": "데이터/동대문구 사회복지시설(노인여가복지시설).csv",
    "senior_job": "데이터/동대문구 사회복지시설(노인일자리지원기관).csv",
    "senior_homecare": "데이터/동대문구 사회복지시설(재가노인복지시설).csv",
    "cctv": "데이터/동대문구_CCTV.csv",
    "intersection": "데이터/동대문구_교차로_위치찐.csv",
    "bus_stop": "데이터/동대문구_버스정류소.csv",
    "hospital": "데이터/동대문구_병의원.csv",
    "market": "데이터/동대문구_전통시장.csv",
    "subway": "데이터/동대문구_지하철역.csv",
    "crosswalk": "데이터/동대문구_횡단보도_중심좌표.csv",
    "led_crosswalk": "시각화용 데이터/서울특별시 동대문구_바닥신호등 현황_20240318.csv",
    "walking_light": "데이터/서울특별시_보행등 위치좌표 현황_20221223.csv",
    "vehicle_entrance": "데이터/동대문구_차량출입구.csv",
    "traffic_camera": "데이터/서울특별시_동대문구_무인교통단속카메라_20240604.csv"
}

# 각 파일의 위도/경도 컬럼명 매핑
coord_columns = {
    "streetlight": {"lat": "위도", "lon": "경도"},
    "senior_leisure": {"lat": "위도", "lon": "경도"},
    "senior_job": {"lat": "위도", "lon": "경도"},
    "senior_homecare": {"lat": "위도", "lon": "경도"},
    "cctv": {"lat": "LA", "lon": "LO"},
    "intersection": {"lat": "위도", "lon": "경도"},
    "bus_stop": {"lat": "Y좌표", "lon": "X좌표"},
    "hospital": {"lat": "위도", "lon": "경도"},
    "market": {"lat": "위도", "lon": "경도"},
    "subway": {"lat": "위도", "lon": "경도"},
    "crosswalk": {"lat": "위도", "lon": "경도"},
    "led_crosswalk": {"lat": "위도", "lon": "경도"},
    "walking_light": {"lat": "위도", "lon": "경도"},
    "vehicle_entrance": {"lat": "위도", "lon": "경도"},
    "traffic_camera": {"lat": "위도", "lon": "경도"}
}

# 안전한 CSV 로딩 함수
def load_csv_safely(path):
    for enc in ['utf-8', 'cp949', 'euc-kr']:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"인코딩 문제로 파일을 불러올 수 없습니다: {path}")

# 모든 데이터프레임 불러오기
dataframes = {name: load_csv_safely(path) for name, path in file_paths.items()}

# 각 데이터프레임의 컬럼명 출력
print("=== 각 데이터프레임의 컬럼명 ===")
for name, df in dataframes.items():
    print(f"\n{name}:")
    print(df.columns.tolist())

# 격자 생성
grid_gdf = create_grid(dongdaemun_bounds)

# 각 시설 유형별로 격자 내 카운트 계산
facility_counts = {}
for name, df in dataframes.items():
    coords = coord_columns[name]
    try:
        counts = count_facilities_in_grid(df, grid_gdf, coords['lon'], coords['lat'])
        facility_counts[name] = counts
    except KeyError as e:
        print(f"\n{name} 데이터프레임 처리 중 오류 발생: {e}")
        print(f"사용 가능한 컬럼: {df.columns.tolist()}")
        facility_counts[name] = np.zeros(len(grid_gdf))
    except Exception as e:
        print(f"\n{name} 데이터프레임 처리 중 예상치 못한 오류 발생: {e}")
        facility_counts[name] = np.zeros(len(grid_gdf))

# 결과를 격자 데이터프레임에 추가
for name, counts in facility_counts.items():
    grid_gdf[name] = counts

# 격자별 총 시설 수 계산
grid_gdf['total_facilities'] = sum(facility_counts.values())

# folium 지도 생성
center_lat = (dongdaemun_bounds['min_lat'] + dongdaemun_bounds['max_lat']) / 2
center_lon = (dongdaemun_bounds['min_lon'] + dongdaemun_bounds['max_lon']) / 2
m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

# 동대문구 경계 추가
folium.GeoJson(
    dongdaemun.to_json(),
    name="동대문구",
    style_function=lambda x: {
        'fillColor': 'none',
        'color': 'blue',
        'weight': 3,
        'fillOpacity': 0
    }
).add_to(m)

# 위험도 지도 추가
for _, row in accident_gdf.iterrows():
    folium.GeoJson(
        data=row.geometry.__geo_interface__,
        style_function=lambda feature, val=row['value']: {
            'fillColor': cm.linear.OrRd_09.scale(min(values), max(values))(val),
            'color': 'none',
            'weight': 0,
            'fillOpacity': 0.6
        }
    ).add_to(m)

# 노인보호구역 추가
for idx, row in protection_data.iterrows():
    # 보호구역 중심점
    point = Point(row["경도"], row["위도"])
    point_gs = gpd.GeoSeries([point], crs='EPSG:4326')
    point_5186 = point_gs.to_crs(epsg=5186).iloc[0]

    # 300m 반경 원 생성
    circle_300_m = point_5186.buffer(300)
    circle_300 = gpd.GeoSeries([circle_300_m], crs='EPSG:5186').to_crs(epsg=4326).iloc[0]
    
    # 팝업 내용 생성
    popup_html = f"""
    <div style="font-family: Arial; font-size: 12px;">
        <h4>{row['대상시설명']}</h4>
        <p>노인보호구역</p>
    </div>
    """

    # 마커 추가
    folium.Marker(
        location=[row["위도"], row["경도"]],
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    # 반경 300m 원 추가
    folium.Circle(
        location=[row["위도"], row["경도"]],
        radius=300,
        color="purple",
        fill=True,
        fill_color="purple",
        fill_opacity=0.2,
        clickable=False,  # 클릭 이벤트를 아래 레이어로 전달
        weight=2
    ).add_to(m)

# 격자를 지도에 추가 (마지막에 추가)
for idx, row in grid_gdf.iterrows():
    # 격자 정보를 HTML로 구성
    popup_html = f"""
    <div style="font-family: Arial; font-size: 12px;">
        <h4>격자 정보</h4>
        <p>총 시설 수: {row['total_facilities']}</p>
        <h5>시설별 개수:</h5>
        <ul>
    """
    
    for name in facility_names.keys():
        count = row[name]
        if count > 0:  # 시설이 있는 경우에만 표시
            popup_html += f"<li>{facility_names[name]}: {count}개</li>"
    
    popup_html += "</ul></div>"
    
    # 격자 스타일 설정 (시설 수에 따라 색상 변경)
    color = 'red' if row['total_facilities'] > 0 else 'lightgray'
    opacity = min(0.6, 0.1 + (row['total_facilities'] / grid_gdf['total_facilities'].max()) * 0.5) if grid_gdf['total_facilities'].max() > 0 else 0.1
    
    # 격자 추가
    folium.GeoJson(
        row.geometry.__geo_interface__,
        style_function=lambda x: {
            'fillColor': color,
            'color': 'black',
            'weight': 1,
            'fillOpacity': opacity
        },
        popup=folium.Popup(popup_html, max_width=300)
    ).add_to(m)

# 위험도 범례 추가
accident_colormap = cm.linear.OrRd_09.scale(min(values), max(values))
accident_colormap.caption = "사고 위험도"
accident_colormap.add_to(m)

# 시설 수 범례 추가
facility_colormap = LinearColormap(
    colors=['lightgray', 'red'],
    vmin=0,
    vmax=grid_gdf['total_facilities'].max() if grid_gdf['total_facilities'].max() > 0 else 1
)
facility_colormap.caption = "총 시설 수"
facility_colormap.add_to(m)

# 지도 표시
m 