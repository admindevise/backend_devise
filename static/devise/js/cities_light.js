const get_countries = async () => {
  const url = Urls.cities_contry();
  const response = await fetch(url, {
    method: 'get'
  });
  return response.json()
}

const get_regions = async (country_id) => {
  const url = Urls.cities_region(country_id);
  const response = await fetch(url, {
    method: 'get'
  });
  return response.json();
}

const get_cities = async (country_id, region_id) => {
  const url = Urls.cities_city(country_id, region_id);
  const response = await fetch(url, {
    method: 'get'
  });
  return response.json();
}

