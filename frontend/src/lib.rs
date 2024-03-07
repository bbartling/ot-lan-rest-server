use serde::{Deserialize, Serialize};
use wasm_bindgen::prelude::*;
use wasm_bindgen::prelude::*;
use wasm_bindgen_futures::JsFuture;
use web_sys::{Headers, Request, RequestInit, RequestMode, Response};

#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    fn log(s: &str);
}

#[derive(Serialize, Deserialize)]
struct User {
    username: String,
    email: String,
    password: String,
}

#[derive(Serialize, Deserialize)]
struct Credentials {
    username: String,
    password: String,
}

// Function to create a user
#[wasm_bindgen]
pub async fn create_user(
    username: String,
    email: String,
    password: String,
    token: String,
) -> Result<JsValue, JsValue> {
    let user = User {
        username,
        email,
        password,
    };
    let data = serde_json::to_string(&user).unwrap();

    let headers = Headers::new().unwrap();
    headers.set("Content-Type", "application/json").unwrap();
    headers
        .set("Authorization", &format!("Bearer {}", token))
        .unwrap(); // Use the token for authorized endpoints

    let mut opts = RequestInit::new();
    opts.method("POST");
    opts.mode(RequestMode::Cors);
    opts.headers(&headers);
    opts.body(Some(&JsValue::from_str(&data)));

    let request = Request::new_with_str_and_init("/api/users/", &opts)?;
    let window = web_sys::window().unwrap();
    let resp_value = JsFuture::from(window.fetch_with_request(&request)).await?;
    let resp: Response = resp_value.dyn_into().unwrap();

    if resp.ok() {
        let json = JsFuture::from(resp.json()?).await?;
        Ok(json)
    } else {
        Err(JsValue::from_str("HTTP request failed"))
    }
}

// Function to login
#[wasm_bindgen]
pub async fn login(username: String, password: String) -> Result<JsValue, JsValue> {
    let creds = Credentials { username, password };
    let data = serde_json::to_string(&creds).unwrap();

    let headers = Headers::new().unwrap();
    headers.set("Content-Type", "application/json").unwrap();

    let mut opts = RequestInit::new();
    opts.method("POST");
    opts.mode(RequestMode::Cors);
    opts.headers(&headers);
    opts.body(Some(&JsValue::from_str(&data)));

    let request = Request::new_with_str_and_init("/api/login/", &opts)?;
    let window = web_sys::window().unwrap();
    let resp_value = JsFuture::from(window.fetch_with_request(&request)).await?;
    let resp: Response = resp_value.dyn_into().unwrap();

    if resp.ok() {
        let json = JsFuture::from(resp.json()?).await?;
        Ok(json)
    } else {
        Err(JsValue::from_str("Login failed"))
    }
}

// Function to fetch users
#[wasm_bindgen]
pub async fn fetch_users() -> Result<JsValue, JsValue> {
    let mut opts = RequestInit::new();
    opts.method("GET");
    opts.mode(RequestMode::Cors);

    let request = Request::new_with_str_and_init("/api/users/", &opts)?;
    let window = web_sys::window().unwrap();
    let resp_value = JsFuture::from(window.fetch_with_request(&request)).await?;
    let resp: Response = resp_value.dyn_into().unwrap();

    if resp.ok() {
        let json = JsFuture::from(resp.json()?).await?;
        Ok(json)
    } else {
        Err(JsValue::from_str("Failed to fetch users"))
    }
}
