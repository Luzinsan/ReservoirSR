using Grpc.Core;
using Simulation.Contracts;
using Simulation.Core.Runtime;

namespace Simulation.Server.Services;

public sealed class SimulationGrpcService(
    SimulationRegistry registry,
    DatasetJobManager jobManager
) : SimulationService.SimulationServiceBase
{
    public override Task<InitializeSimulationResponse> InitializeSimulation(
        InitializeSimulationRequest request,
        ServerCallContext context
    )
    {
        string simulationId = string.IsNullOrWhiteSpace(request.SimulationId)
            ? Guid.NewGuid().ToString("N")
            : request.SimulationId;

        var runtime = registry.CreateOrReplace(simulationId);
        runtime.Initialize(SimulationConfigMapper.ToCoreConfig(request.Config));

        return Task.FromResult(new InitializeSimulationResponse
        {
            SimulationId = simulationId,
            Ok = true,
            Message = "Initialized",
            Nx = runtime.Engine.NX,
            Nz = runtime.Engine.NZ
        });
    }

    public override Task<StepSimulationResponse> StepSimulation(
        StepSimulationRequest request,
        ServerCallContext context
    )
    {
        if (!registry.TryGet(request.SimulationId, out var runtime))
        {
            return Task.FromResult(new StepSimulationResponse
            {
                Ok = false,
                Message = $"Simulation '{request.SimulationId}' not found."
            });
        }

        try
        {
            var result = runtime.Step(request.StepCount <= 0 ? 1 : request.StepCount);
            return Task.FromResult(new StepSimulationResponse
            {
                Ok = true,
                Message = "Stepped",
                StepsPerformed = result.StepsPerformed,
                Time = result.Time,
                Ai = result.Ai,
                Ait = result.Ait,
                Aib = result.Aib,
                PZab = result.Pzab,
                QFld = result.QFld,
                Diss = result.Diss,
                Disq = result.Disq
            });
        }
        catch (Exception ex)
        {
            return Task.FromResult(new StepSimulationResponse
            {
                Ok = false,
                Message = ex.Message
            });
        }
    }

    public override Task<GetFieldsResponse> GetFields(GetFieldsRequest request, ServerCallContext context)
    {
        if (!registry.TryGet(request.SimulationId, out var runtime))
        {
            return Task.FromResult(new GetFieldsResponse
            {
                Ok = false,
                Message = $"Simulation '{request.SimulationId}' not found."
            });
        }

        var fields = request.Fields.Count == 0 ? ["P", "ST", "SB"] : request.Fields;
        var response = new GetFieldsResponse
        {
            Ok = true,
            Message = "OK",
            Nx = runtime.Engine.NX,
            Nz = runtime.Engine.NZ
        };

        foreach (string field in fields)
        {
            var data = new FieldData { Name = field };
            data.Values.AddRange(runtime.GetField(field.ToUpperInvariant()));
            response.Data.Add(data);
        }

        return Task.FromResult(response);
    }

    public override Task<RunDatasetJobResponse> RunDatasetJob(RunDatasetJobRequest request, ServerCallContext context)
    {
        try
        {
            var spec = new RunDatasetSpec(
                request.JobId,
                string.IsNullOrWhiteSpace(request.OutputDir) ? "dataset_out" : request.OutputDir,
                SimulationConfigMapper.ToCoreConfig(request.Config),
                request.TrajectorySteps > 0 ? request.TrajectorySteps : Math.Max(request.MaxSteps, 1),
                request.CaptureEveryStep
            );

            var status = jobManager.Start(spec);
            return Task.FromResult(new RunDatasetJobResponse
            {
                Ok = true,
                Message = "Job started",
                JobId = status.JobId
            });
        }
        catch (Exception ex)
        {
            return Task.FromResult(new RunDatasetJobResponse
            {
                Ok = false,
                Message = ex.Message,
                JobId = request.JobId
            });
        }
    }

    public override Task<GetJobStatusResponse> GetJobStatus(GetJobStatusRequest request, ServerCallContext context)
    {
        if (!jobManager.TryGet(request.JobId, out var status))
        {
            return Task.FromResult(new GetJobStatusResponse
            {
                JobId = request.JobId,
                State = "not_found",
                Message = "Job not found."
            });
        }

        return Task.FromResult(new GetJobStatusResponse
        {
            JobId = status.JobId,
            State = status.State,
            Message = status.Message,
            StepsDone = status.StepsDone,
            StepsTotal = status.StepsTotal,
            OutputDir = status.OutputDir
        });
    }

    public override Task<CancelJobResponse> CancelJob(CancelJobRequest request, ServerCallContext context)
    {
        bool ok = jobManager.Cancel(request.JobId);
        return Task.FromResult(new CancelJobResponse
        {
            Ok = ok,
            Message = ok ? "Cancelled." : "Job not found."
        });
    }
}
