/**
 * monitoringAreas.js — Live Clustering Phase 4
 *
 * Static mirror of the 50 Bengaluru monitoring areas defined in
 * backend/app/modules/live_clustering/area_service.py.
 *
 * Used for the preset dropdown — no network request needed.
 * Kept isolated inside Live Clustering.
 */

export const MONITORING_AREAS = [
  // South / ORR
  { id: "silk_board",          name: "Silk Board Junction",            latitude: 12.9174, longitude: 77.6228, category: "South / ORR" },
  { id: "bommanahalli",        name: "Bommanahalli",                   latitude: 12.9091, longitude: 77.6176, category: "South / ORR" },
  { id: "hsr_layout",          name: "HSR Layout Sector 1",            latitude: 12.9116, longitude: 77.6474, category: "South / ORR" },
  { id: "btm_layout",          name: "BTM Layout",                     latitude: 12.9166, longitude: 77.6101, category: "South / ORR" },
  { id: "jp_nagar",            name: "JP Nagar",                       latitude: 12.9102, longitude: 77.5922, category: "South / ORR" },
  { id: "banashankari",        name: "Banashankari",                   latitude: 12.9259, longitude: 77.5461, category: "South / ORR" },
  { id: "jayanagar",           name: "Jayanagar 4th Block",            latitude: 12.9308, longitude: 77.5832, category: "South" },
  { id: "electronic_city",     name: "Electronic City Phase 1",        latitude: 12.8446, longitude: 77.6613, category: "South / ORR" },
  // East / Whitefield
  { id: "whitefield",          name: "Whitefield",                     latitude: 12.9698, longitude: 77.7499, category: "East / Whitefield" },
  { id: "marathahalli",        name: "Marathahalli",                   latitude: 12.9591, longitude: 77.6974, category: "East / Whitefield" },
  { id: "kr_puram",            name: "KR Puram",                       latitude: 13.0079, longitude: 77.6965, category: "East / Whitefield" },
  { id: "brookefield",         name: "Brookefield",                    latitude: 12.9670, longitude: 77.7301, category: "East / Whitefield" },
  { id: "itpl",                name: "ITPL Main Road",                  latitude: 12.9863, longitude: 77.7274, category: "East / Whitefield" },
  { id: "kadugodi",            name: "Kadugodi",                       latitude: 12.9923, longitude: 77.7702, category: "East / Whitefield" },
  { id: "varthur",             name: "Varthur",                        latitude: 12.9407, longitude: 77.7473, category: "East / Whitefield" },
  { id: "harlur_road",         name: "Harlur Road",                    latitude: 12.9156, longitude: 77.6722, category: "East" },
  // North / Hebbal
  { id: "hebbal",              name: "Hebbal Flyover",                  latitude: 13.0350, longitude: 77.5946, category: "North / Hebbal" },
  { id: "bellary_road",        name: "Bellary Road / Airport",          latitude: 13.0622, longitude: 77.5899, category: "North / Hebbal" },
  { id: "yelahanka",           name: "Yelahanka",                      latitude: 13.1004, longitude: 77.5963, category: "North" },
  { id: "thanisandra",         name: "Thanisandra",                    latitude: 13.0600, longitude: 77.6334, category: "North" },
  { id: "kogilu",              name: "Kogilu Cross",                    latitude: 13.0738, longitude: 77.6083, category: "North" },
  { id: "banaswadi",           name: "Banaswadi",                      latitude: 13.0108, longitude: 77.6562, category: "North-East" },
  { id: "kalyan_nagar",        name: "Kalyan Nagar",                   latitude: 13.0206, longitude: 77.6499, category: "North-East" },
  { id: "rt_nagar",            name: "RT Nagar",                       latitude: 13.0219, longitude: 77.5957, category: "North" },
  // Central / CBD
  { id: "mg_road",             name: "MG Road",                        latitude: 12.9758, longitude: 77.6094, category: "Central / CBD" },
  { id: "brigade_road",        name: "Brigade Road",                   latitude: 12.9728, longitude: 77.6075, category: "Central / CBD" },
  { id: "commercial_street",   name: "Commercial Street",              latitude: 12.9815, longitude: 77.6069, category: "Central / CBD" },
  { id: "majestic",            name: "Majestic / KSR Station",         latitude: 12.9774, longitude: 77.5714, category: "Central / CBD" },
  { id: "shivajinagar",        name: "Shivajinagar",                   latitude: 12.9850, longitude: 77.6013, category: "Central" },
  { id: "cunningham_road",     name: "Cunningham Road",                latitude: 12.9918, longitude: 77.5973, category: "Central" },
  // West / Rajajinagar
  { id: "rajajinagar",         name: "Rajajinagar",                    latitude: 12.9974, longitude: 77.5528, category: "West" },
  { id: "tumkur_road",         name: "Tumkur Road",                    latitude: 13.0162, longitude: 77.5454, category: "West" },
  { id: "peenya",              name: "Peenya Industrial Area",          latitude: 13.0290, longitude: 77.5188, category: "West" },
  { id: "yeshwanthpur",        name: "Yeshwanthpur Circle",            latitude: 13.0218, longitude: 77.5534, category: "West" },
  { id: "dasarahalli",         name: "Dasarahalli",                    latitude: 13.0541, longitude: 77.5151, category: "West" },
  { id: "kengeri",             name: "Kengeri",                        latitude: 12.9081, longitude: 77.4802, category: "West" },
  // Koramangala / Indiranagar
  { id: "koramangala",         name: "Koramangala 5th Block",          latitude: 12.9352, longitude: 77.6245, category: "Koramangala" },
  { id: "koramangala_1",       name: "Koramangala 1st Block",          latitude: 12.9381, longitude: 77.6144, category: "Koramangala" },
  { id: "indiranagar",         name: "Indiranagar 100ft Road",          latitude: 12.9784, longitude: 77.6408, category: "Indiranagar" },
  { id: "domlur",              name: "Domlur",                         latitude: 12.9601, longitude: 77.6388, category: "Indiranagar" },
  { id: "hal_airport_road",    name: "HAL Old Airport Road",           latitude: 12.9618, longitude: 77.6478, category: "Indiranagar" },
  // ORR / Sarjapur
  { id: "sarjapur",            name: "Sarjapur Road",                  latitude: 12.9096, longitude: 77.6829, category: "South-East / Sarjapur" },
  { id: "bellandur",           name: "Bellandur",                      latitude: 12.9258, longitude: 77.6763, category: "South-East / Sarjapur" },
  { id: "carmelram",           name: "Carmelram / Ibbalur",            latitude: 12.8987, longitude: 77.6676, category: "South-East" },
  { id: "panathur",            name: "Panathur",                       latitude: 12.9420, longitude: 77.7180, category: "South-East" },
  // Outer Areas
  { id: "kia_airport",         name: "Kempegowda International Airport", latitude: 13.1986, longitude: 77.7066, category: "Outer North" },
  { id: "devanahalli",         name: "Devanahalli Town",               latitude: 13.2470, longitude: 77.7130, category: "Outer North" },
  { id: "nelamangala",         name: "Nelamangala",                    latitude: 13.0994, longitude: 77.3911, category: "Outer West" },
  { id: "electronic_city_ph2", name: "Electronic City Phase 2",        latitude: 12.8344, longitude: 77.6643, category: "Outer South" },
  { id: "hoskote",             name: "Hoskote",                        latitude: 13.0688, longitude: 77.7978, category: "Outer East" },
  { id: "bannerghatta_road",   name: "Bannerghatta Road",              latitude: 12.8777, longitude: 77.5978, category: "South" },
];

/** Group areas by category for the grouped dropdown. */
export function getAreasByCategory() {
  const grouped = {};
  for (const area of MONITORING_AREAS) {
    if (!grouped[area.category]) grouped[area.category] = [];
    grouped[area.category].push(area);
  }
  return grouped;
}

/** Find an area by its id. */
export function findAreaById(id) {
  return MONITORING_AREAS.find((a) => a.id === id) ?? null;
}
