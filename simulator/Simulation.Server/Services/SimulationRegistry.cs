using Simulation.Core.Runtime;
using System.Collections.Concurrent;

namespace Simulation.Server.Services;

public sealed class SimulationRegistry
{
    private readonly ConcurrentDictionary<string, SimulationRuntime> _runtimes = new(StringComparer.Ordinal);

    public SimulationRuntime CreateOrReplace(string simulationId)
    {
        var runtime = new SimulationRuntime();
        _runtimes.AddOrUpdate(simulationId, runtime, (_, _) => runtime);
        return runtime;
    }

    public SimulationRuntime GetOrCreate(string simulationId)
    {
        return _runtimes.GetOrAdd(simulationId, _ => new SimulationRuntime());
    }

    public bool TryGet(string simulationId, out SimulationRuntime runtime)
    {
        return _runtimes.TryGetValue(simulationId, out runtime!);
    }
}
