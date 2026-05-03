using Simulation.Core.Runtime;
using System.Collections.Concurrent;

namespace Simulation.Server.Services;

public sealed class SimulationRegistry
{
    private readonly ConcurrentDictionary<string, SimulationRuntime> _runtimes = new(StringComparer.Ordinal);

    public void AddOrReplace(string simulationId, SimulationRuntime runtime)
    {
        _runtimes.AddOrUpdate(simulationId, runtime, (_, _) => runtime);
    }

    public bool Remove(string simulationId)
    {
        return _runtimes.TryRemove(simulationId, out _);
    }

    public bool TryGet(string simulationId, out SimulationRuntime runtime)
    {
        return _runtimes.TryGetValue(simulationId, out runtime!);
    }
}
