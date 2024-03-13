

import pingpong_pb2, pingpong_pb2_grpc
import asyncio
import grpc

'''
For testing purposes only to see if
client can ping pong with the server
'''

async def run():
    # Assuming your server is running on localhost:50051
    async with grpc.aio.insecure_channel('localhost:50051') as channel:
        stub = pingpong_pb2_grpc.PingPongStub(channel)
        response = await stub.Ping(pingpong_pb2.PingRequest(ping="ping"))
        print("PingPong client received: " + response.pong)

if __name__ == '__main__':
    asyncio.run(run())
