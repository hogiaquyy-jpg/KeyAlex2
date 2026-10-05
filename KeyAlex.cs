using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace AlexCheatShop
{
    public static class KeyAPI
    {
        private static readonly HttpClient client = new HttpClient { Timeout = TimeSpan.FromSeconds(30) };
        private const string API_BASE = "https://keyalex2.onrender.com/api/v1";

        private static string DeviceId()
        {
            return Environment.MachineName;
        }

        public static LoginResponse loginResponse = new LoginResponse();

        // ===== LOGIN =====
        public static async Task<bool> Login(string username, string password)
        {
            try
            {
                var data = new { username, password };
                string json = JsonConvert.SerializeObject(data);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await client.PostAsync($"{API_BASE}/auth/login", content);
                string resultJson = await response.Content.ReadAsStringAsync();
                loginResponse = JsonConvert.DeserializeObject<LoginResponse>(resultJson);
                return loginResponse.success;
            }
            catch (Exception ex)
            {
                loginResponse = new LoginResponse { success = false, message = $"Lỗi: {ex.Message}" };
                return false;
            }
        }

        // ===== CHECK KEY =====
        public static async Task<KeyCheckResponse> CheckKey(string keyCode)
        {
            try
            {
                var data = new { license_key = keyCode, device_id = DeviceId() };
                string json = JsonConvert.SerializeObject(data);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await client.PostAsync($"{API_BASE}/validate", content);
                string resultJson = await response.Content.ReadAsStringAsync();
                if (!response.IsSuccessStatusCode)
                    return new KeyCheckResponse { valid = false, reason = $"Server tra ve loi {(int)response.StatusCode}: {resultJson}" };
                var parsed = JsonConvert.DeserializeObject<KeyCheckResponse>(resultJson);
                if (parsed == null)
                    return new KeyCheckResponse { valid = false, reason = "Server tra ve du lieu la!" };
                return parsed;
            }
            catch (TaskCanceledException)
            {
                return new KeyCheckResponse { valid = false, reason = "Khong ket noi duoc server (timeout). Kiem tra URL server + mang!" };
            }
            catch (HttpRequestException ex)
            {
                return new KeyCheckResponse { valid = false, reason = $"Khong ket noi duoc server: {ex.Message}" };
            }
            catch (Exception ex)
            {
                return new KeyCheckResponse { valid = false, reason = $"Lỗi: {ex.Message}" };
            }
        }

        // ===== USE KEY =====
        public static async Task<bool> UseKey(string keyCode)
        {
            try
            {
                var data = new { license_key = keyCode, device_id = DeviceId() };
                string json = JsonConvert.SerializeObject(data);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await client.PostAsync($"{API_BASE}/activate", content);
                string resultJson = await response.Content.ReadAsStringAsync();
                if (!response.IsSuccessStatusCode)
                    return false;
                var result = JsonConvert.DeserializeObject<dynamic>(resultJson);
                if (result == null)
                    return true; // 200 OK coi nhu kich hoat xong
                if (result.success != null)
                    return result.success == true;
                if (result.valid != null)
                    return result.valid == true;
                return result.detail == null;
            }
            catch
            {
                return false;
            }
        }

        // ===== GET ACTIVE KEYS =====
        public static async Task<List<KeyInfo>> GetActiveKeys()
        {
            try
            {
                var response = await client.GetAsync($"{API_BASE}/keys/active");
                string resultJson = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<List<KeyInfo>>(resultJson) ?? new List<KeyInfo>();
            }
            catch
            {
                return new List<KeyInfo>();
            }
        }

        // ===== GET ALL KEYS =====
        public static async Task<List<KeyInfo>> GetAllKeys()
        {
            try
            {
                var response = await client.GetAsync($"{API_BASE}/keys");
                string resultJson = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<List<KeyInfo>>(resultJson) ?? new List<KeyInfo>();
            }
            catch
            {
                return new List<KeyInfo>();
            }
        }

        // ===== BAN KEY =====
        public static async Task<bool> BanKey(int keyId)
        {
            try
            {
                var response = await client.PostAsync($"{API_BASE}/keys/ban/{keyId}", null);
                string resultJson = await response.Content.ReadAsStringAsync();
                var result = JsonConvert.DeserializeObject<dynamic>(resultJson);
                return result.success == true;
            }
            catch
            {
                return false;
            }
        }

        // ===== UNBAN KEY =====
        public static async Task<bool> UnbanKey(int keyId)
        {
            try
            {
                var response = await client.PostAsync($"{API_BASE}/keys/unban/{keyId}", null);
                string resultJson = await response.Content.ReadAsStringAsync();
                var result = JsonConvert.DeserializeObject<dynamic>(resultJson);
                return result.success == true;
            }
            catch
            {
                return false;
            }
        }

        // ===== CREATE KEY =====
        public static async Task<KeyCreateResponse> CreateKey(int productId, int userId, string username)
        {
            try
            {
                var data = new { product_id = productId, user_id = userId, username };
                string json = JsonConvert.SerializeObject(data);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await client.PostAsync($"{API_BASE}/keys/create", content);
                string resultJson = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<KeyCreateResponse>(resultJson);
            }
            catch (Exception ex)
            {
                return new KeyCreateResponse { success = false, message = $"Lỗi: {ex.Message}" };
            }
        }

        // ===== GET PENDING PAYMENTS =====
        public static async Task<List<PaymentInfo>> GetPendingPayments()
        {
            try
            {
                var response = await client.GetAsync($"{API_BASE}/payments/pending");
                string resultJson = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<List<PaymentInfo>>(resultJson) ?? new List<PaymentInfo>();
            }
            catch
            {
                return new List<PaymentInfo>();
            }
        }

        // ===== CONFIRM PAYMENT =====
        public static async Task<PaymentConfirmResponse> ConfirmPayment(string paymentId)
        {
            try
            {
                var response = await client.PostAsync($"{API_BASE}/payments/confirm/{paymentId}", null);
                string resultJson = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<PaymentConfirmResponse>(resultJson);
            }
            catch (Exception ex)
            {
                return new PaymentConfirmResponse { success = false, message = $"Lỗi: {ex.Message}" };
            }
        }

        // ===== GET STATS =====
        public static async Task<StatsResponse> GetStats()
        {
            try
            {
                var response = await client.GetAsync($"{API_BASE}/stats");
                string resultJson = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<StatsResponse>(resultJson) ?? new StatsResponse();
            }
            catch
            {
                return new StatsResponse();
            }
        }
    }

    // ===== RESPONSE CLASSES =====
    public class LoginResponse
    {
        public bool success { get; set; }
        public string message { get; set; }
        public string token { get; set; }
        public UserInfo user { get; set; }
    }

    public class UserInfo
    {
        public int id { get; set; }
        public string username { get; set; }
        public int total_spent { get; set; }
        public string role { get; set; }
    }

    public class KeyCheckResponse
    {
        public bool valid { get; set; }
        public string product { get; set; }
        public string username { get; set; }
        public string expires { get; set; }
        public string reason { get; set; }
    }

    public class KeyInfo
    {
        public int id { get; set; }
        public string key { get; set; }
        public string product { get; set; }
        public string username { get; set; }
        public string created { get; set; }
        public string expires { get; set; }
        public bool used { get; set; }
        public bool banned { get; set; }
    }

    public class KeyCreateResponse
    {
        public bool success { get; set; }
        public string key { get; set; }
        public string expires { get; set; }
        public string message { get; set; }
    }

    public class PaymentInfo
    {
        public string payment_id { get; set; }
        public string username { get; set; }
        public int amount { get; set; }
        public string created_at { get; set; }
    }

    public class PaymentConfirmResponse
    {
        public bool success { get; set; }
        public string key { get; set; }
        public string expires { get; set; }
        public string message { get; set; }
    }

    public class StatsResponse
    {
        public int total_keys { get; set; }
        public int active_keys { get; set; }
        public int pending_payments { get; set; }
        public int total_revenue { get; set; }
    }
}