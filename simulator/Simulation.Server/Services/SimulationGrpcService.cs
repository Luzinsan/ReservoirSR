using Grpc.Core;
using Simulation.Contracts;
using Simulation.Core.Runtime;

namespace Simulation.Server.Services;

public sealed class SimulationGrpcService(
    SimulationRegistry registry,
    DatasetJobManager jobManager,
    ILogger<SimulationGrpcService> logger
) : SimulationService.SimulationServiceBase
{
    public override Task<InitializeSimulationResponse> InitializeSimulation(
        InitializeSimulationRequest request,
        ServerCallContext context
    )
    {
        try
        {
            string simulationId = string.IsNullOrWhiteSpace(request.SimulationId)
                ? Guid.NewGuid().ToString("N")
                : request.SimulationId;

            logger.LogInformation("Initialize simulation {SimulationId}", simulationId);

            var runtime = new SimulationRuntime();
            runtime.Initialize(SimulationConfigMapper.ToCoreConfig(request.Config));
            registry.AddOrReplace(simulationId, runtime);

            var metadata = runtime.GetMetadata();
            return Task.FromResult(new InitializeSimulationResponse
            {
                SimulationId = simulationId,
                Ok = true,
                Message = "Initialized",
                Nx = metadata.Nx,
                Nz = metadata.Nz
            });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Initialization failed for simulation {SimulationId}", request.SimulationId);
            return Task.FromResult(new InitializeSimulationResponse
            {
                SimulationId = request.SimulationId,
                Ok = false,
                Message = ex.Message
            });
        }
    }

    public override Task<StepSimulationResponse> StepSimulation(
        StepSimulationRequest request,
        ServerCallContext context
    )
    {
        if (!registry.TryGet(request.SimulationId, out var runtime))
        {
            logger.LogWarning("Step requested for unknown simulation {SimulationId}", request.SimulationId);
            return Task.FromResult(new StepSimulationResponse
            {
                Ok = false,
                Message = $"Simulation '{request.SimulationId}' not found."
            });
        }

        try
        {
            var result = runtime.Step(request.StepCount <= 0 ? 1 : request.StepCount);
            logger.LogDebug(
                "Stepped simulation {SimulationId}: steps={Steps} time={Time}",
                request.SimulationId,
                result.StepsPerformed,
                result.Time
            );
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
                Disq = result.Disq,
                Tbt = result.Tbt,
                Tb = result.Tb,
                Tt = result.Tt,
                QOilTotal = result.QOilTotal,
                QOilBlocks = result.QOilBlocks,
                QOilFractures = result.QOilFractures
            });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Step failed for simulation {SimulationId}", request.SimulationId);
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
            logger.LogWarning("Field request for unknown simulation {SimulationId}", request.SimulationId);
            return Task.FromResult(new GetFieldsResponse
            {
                Ok = false,
                Message = $"Simulation '{request.SimulationId}' not found."
            });
        }

        var fields = request.Fields.Count == 0 ? ["P", "ST", "SB"] : request.Fields;
        try
        {
            var metadata = runtime.GetMetadata();
            var response = new GetFieldsResponse
            {
                Ok = true,
                Message = "OK",
                Nx = metadata.Nx,
                Nz = metadata.Nz
            };

            foreach (string field in fields)
            {
                var data = new FieldData { Name = field };
                data.Values.Capacity = metadata.Nx * metadata.Nz;
                runtime.GetFieldTo(field.ToUpperInvariant(), data.Values);
                response.Data.Add(data);
            }
            logger.LogDebug("Returned {FieldCount} fields for simulation {SimulationId}", response.Data.Count, request.SimulationId);

            return Task.FromResult(response);
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Field export failed for simulation {SimulationId}", request.SimulationId);
            return Task.FromResult(new GetFieldsResponse
            {
                Ok = false,
                Message = ex.Message
            });
        }
    }

    public override Task<RunDatasetJobResponse> RunDatasetJob(RunDatasetJobRequest request, ServerCallContext context)
    {
        try
        {
            var spec = new RunDatasetSpec(
                request.JobId,
                string.IsNullOrWhiteSpace(request.OutputDir) ? "dataset_out" : request.OutputDir,
                SimulationConfigMapper.ToCoreConfig(request.Config),
                request.Steps > 0 ? request.Steps : 1,
                request.SnapshotStride > 0 ? request.SnapshotStride : 1
            );

            var status = jobManager.Start(spec);
            logger.LogInformation("Dataset job started {JobId} output={OutputDir} steps={Steps}", status.JobId, spec.OutputDir, spec.TotalSteps);
            return Task.FromResult(new RunDatasetJobResponse
            {
                Ok = true,
                Message = "Job started",
                JobId = status.JobId
            });
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Dataset job start failed for {JobId}", request.JobId);
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
            logger.LogWarning("Status requested for unknown job {JobId}", request.JobId);
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
            OutputPath = status.OutputPath
        });
    }

    public override Task<CancelJobResponse> CancelJob(CancelJobRequest request, ServerCallContext context)
    {
        bool ok = jobManager.Cancel(request.JobId);
        logger.LogInformation("Cancel job {JobId}: {Result}", request.JobId, ok ? "ok" : "not_found");
        return Task.FromResult(new CancelJobResponse
        {
            Ok = ok,
            Message = ok ? "Cancelled." : "Job not found."
        });
    }
}
