import 'bootstrap/dist/css/bootstrap.min.css';
import 'leaflet/dist/leaflet.css';
import { useEffect, useRef, useState } from 'react';
import L, { Map as LeafletMap, Marker as LeafletMarker, Polyline as LeafletPolyline } from 'leaflet';
import { renderToStaticMarkup } from 'react-dom/server';
import { FaMapMarkerAlt } from 'react-icons/fa';

interface Site {
    name: string;
    latitude: number;
    longitude: number;
    distance: number;
    country: string;
    year_inscribed: number;
    description: string;
}

const LAMBDA_URL = import.meta.env.VITE_LAMBDA_URL;

const markerHtml = renderToStaticMarkup(
    <div style={{ color: '#2b7cff', fontSize: '2rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <FaMapMarkerAlt />
    </div>
);

const customIcon = L.divIcon({
    className: "",
    html: markerHtml,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
});

function Home() {
    const mapRef = useRef<HTMLDivElement>(null);
    const leafletMap = useRef<LeafletMap | null>(null);
    const [locationStatus, setLocationStatus] = useState('');
    const [currentAddress, setCurrentAddress] = useState('');
    const [sites, setSites] = useState<Site[]>([]);
    const [selectedSite, setSelectedSite] = useState<Site | null>(null);
    const [addressInput, setAddressInput] = useState('');
    const markerRef = useRef<LeafletMarker | null>(null);
    const siteMarkersRef = useRef<LeafletMarker[]>([]);
    const lineRef = useRef<LeafletPolyline | null>(null);
    const [siteAddresses, setSiteAddresses] = useState<{ [key: number]: string }>({});

    // 地図の初期化
    useEffect(() => {
        if (mapRef.current && !leafletMap.current) {
            leafletMap.current = L.map(mapRef.current).setView([35.6812, 139.7671], 6);
            L.tileLayer('https://tile.openstreetmap.jp/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(leafletMap.current);
        }
    }, []);

    // サイト選択時の地図更新
    useEffect(() => {
        if (!leafletMap.current || !selectedSite || !markerRef.current) return;
        // 既存のサイトマーカー削除
        siteMarkersRef.current.forEach(m => leafletMap.current!.removeLayer(m));
        siteMarkersRef.current = [];
        // サイトマーカー追加
        const marker = L.marker([selectedSite.latitude, selectedSite.longitude], { icon: customIcon })
            .addTo(leafletMap.current)
            .bindPopup(selectedSite.name)
            .openPopup();
        siteMarkersRef.current.push(marker);
        // ライン描画
        if (lineRef.current) {
            leafletMap.current.removeLayer(lineRef.current);
        }
        lineRef.current = L.polyline([
            [markerRef.current.getLatLng().lat, markerRef.current.getLatLng().lng],
            [selectedSite.latitude, selectedSite.longitude],
        ], { color: 'red', weight: 3, dashArray: '5, 10' }).addTo(leafletMap.current);
        leafletMap.current.setView([selectedSite.latitude, selectedSite.longitude], 10);
        // 住所取得
        if (!siteAddresses[selectedSite.latitude]) {
            getAddress(selectedSite.latitude, selectedSite.longitude).then(addr => {
                setSiteAddresses(prev => ({ ...prev, [selectedSite.latitude]: addr }));
            });
        }
    }, [selectedSite]);

    // 逆ジオコーディング
    async function getAddress(lat: number, lng: number) {
        try {
            const response = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`
            );
            const data = await response.json();
            return data.display_name;
        } catch {
            return '住所を取得できませんでした';
        }
    }

    // 住所→座標
    async function getCoordinates(address: string) {
        try {
            const response = await fetch(
                `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=1`
            );
            const data = await response.json();
            if (data.length > 0) {
                return {
                    lat: parseFloat(data[0].lat),
                    lng: parseFloat(data[0].lon),
                };
            }
            return null;
        } catch {
            return null;
        }
    }

    // サイト検索API
    async function searchNearestSites(lat: number, lng: number) {
        if (!leafletMap.current) return;
        setLocationStatus('位置情報を取得中...');
        // 既存マーカー削除
        if (markerRef.current) {
            leafletMap.current.removeLayer(markerRef.current);
        }
        markerRef.current = L.marker([lat, lng], { icon: customIcon })
            .addTo(leafletMap.current)
            // .bindPopup('現在地')
            .openPopup();
        leafletMap.current.setView([lat, lng], 12);
        // 住所取得
        const address = await getAddress(lat, lng);
        setCurrentAddress(`現在地: ${address}`);
        // API呼び出し
        try {
            const response = await fetch(
                LAMBDA_URL,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ latitude: lat, longitude: lng }),
                }
            );
            const data = await response.json();
            if (data.error) {
                setLocationStatus(data.error);
                setSites([]);
                return;
            }
            setSites(data);
            setSelectedSite(data[0] || null);
            setLocationStatus('位置情報を取得しました');
        } catch {
            setLocationStatus('エラーが発生しました');
        }
    }

    // 現在地ボタン
    const handleGetLocation = () => {
        setLocationStatus('位置情報を取得中...');
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    await searchNearestSites(position.coords.latitude, position.coords.longitude);
                },
                () => {
                    setLocationStatus('位置情報の取得に失敗しました');
                }
            );
        } else {
            setLocationStatus('このブラウザは位置情報をサポートしていません');
        }
    };

    // 住所検索ボタン
    const handleSearchByAddress = async () => {
        if (!addressInput.trim()) {
            setLocationStatus('住所を入力してください');
            return;
        }
        setLocationStatus('住所を検索中...');
        const coordinates = await getCoordinates(addressInput);
        if (coordinates) {
            await searchNearestSites(coordinates.lat, coordinates.lng);
        } else {
            setLocationStatus('住所が見つかりませんでした');
        }
    };

    return (
        <div className="container mt-5">
            <div className="row">
                <div className="col-md-6">
                    <div className="card">
                        <div className="card-body">
                            <button className="btn btn-primary" onClick={handleGetLocation}>現在地を取得</button>
                            <div className="address-input">
                                <h5 className="card-title mt-3">郵便番号から検索</h5>
                                <div className="input-group">
                                    <input type="text" className="form-control" placeholder="住所を入力"
                                        value={addressInput} onChange={e => setAddressInput(e.target.value)} />
                                    <button className="btn btn-outline-primary" onClick={handleSearchByAddress}>検索</button>
                                </div>
                                <div className="mt-2">{locationStatus}</div>
                                <div className="address-info"><p>{currentAddress}</p></div>
                            </div>
                        </div>
                    </div>
                    <div className="card result-card" style={{ display: sites.length > 0 ? 'block' : 'none' }}>
                        <div className="card-body">
                            <h5 className="card-title">最寄りの世界遺産</h5>
                            <div>
                                {sites.map((site, idx) => (
                                    <div key={idx} className={`site-item${selectedSite === site ? ' active-site' : ''}`}
                                        onClick={() => setSelectedSite(site)}>
                                        <div className="d-flex justify-content-between align-items-center">
                                            <h6 className="mb-0">{idx + 1}. {site.name}</h6>
                                            <span className="text-muted">{site.distance} km</span>
                                        </div>
                                        {selectedSite === site && (
                                            <div className="site-details" style={{ display: 'block' }}>
                                                <p className="mb-1">国: {site.country}</p>
                                                <p className="mb-1">登録年: {site.year_inscribed}</p>
                                                <p className="mb-1">{site.description}</p>
                                                <div className="site-address">
                                                    住所: {siteAddresses[site.latitude] || '取得中...'}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
                <div className="col-md-6">
                    <div id="map" ref={mapRef} style={{ height: 400, width: '100%', marginTop: 20 }}></div>
                </div>
            </div>
        </div>
    );
}

export default Home; 