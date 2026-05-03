using Simulation.Server.Services;
using Microsoft.AspNetCore.Server.Kestrel.Core;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(options =>
{
    options.ListenAnyIP(5000, listenOptions => { listenOptions.Protocols = HttpProtocols.Http2; });
});

builder.Services.AddGrpc();
builder.Services.AddSingleton<SimulationRegistry>();
builder.Services.AddSingleton<DatasetJobManager>();

var app = builder.Build();

app.MapGrpcService<SimulationGrpcService>();
app.MapGet("/", () => "Simulation.Server is running.");

app.Run();
