/* eslint-disable no-undef */
let base_url = window.location.origin;
if (base_url === 'http://localhost:5173') {
  base_url = 'http://localhost:8080';
}
export const API_URL = base_url + '/api';
export const LOADING_DELAY = 300;
export let PAGINATION = {
  limit: 10,
};