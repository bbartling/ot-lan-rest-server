import pingpong_pb2, pingpong_pb2_grpc
import grpc
import asyncio


class PingPongServicer(pingpong_pb2_grpc.PingPongServicer):
    async def Ping(self, request, context):
        print("Ping request: \n", request)
        #print("Ping context: \n", context)
        return pingpong_pb2.PongReply(pong="pong")

async def serve() -> None:
    server = grpc.aio.server()
    pingpong_pb2_grpc.add_PingPongServicer_to_server(PingPongServicer(), server)
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    print(f'Starting server on {listen_addr}')
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())
