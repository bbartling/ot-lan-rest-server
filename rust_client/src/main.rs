use tonic::transport::Channel;
use tokio::runtime::Runtime;

pub mod pingpong {
    tonic::include_proto!("pingpong"); // The string specified here must match the proto package name
}

use pingpong::ping_pong_client::PingPongClient;
use pingpong::PingRequest;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Tokio async runtime
    let rt = Runtime::new().unwrap();

    rt.block_on(async {
        let mut client = PingPongClient::connect("http://localhost:50051").await?;

        let request = tonic::Request::new(PingRequest {
            ping: "ping".into(),
        });

        let response = client.ping(request).await?;

        println!("PingPong client received: {:?}", response.into_inner().pong);

        Ok(())
    })
}
