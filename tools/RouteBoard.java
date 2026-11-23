// Minimal local Freerouting 2.0.1 library runner. Explicitly applies the stop
// pass and writes SES synchronously, avoiding CLI scheduler/export races.
import app.freerouting.Freerouting;
import app.freerouting.settings.GlobalSettings;
import app.freerouting.settings.RouterSettings;
import app.freerouting.core.*;
import app.freerouting.board.ItemIdentificationNumberGenerator;
import app.freerouting.interactive.HeadlessBoardManager;
import app.freerouting.autoroute.BatchAutorouter;
import app.freerouting.designforms.specctra.SpecctraSesFileWriter;
import java.nio.file.*;
import java.util.UUID;

public class RouteBoard {
    public static void main(String[] args) throws Exception {
        if (args.length < 3 || args.length > 4) throw new IllegalArgumentException("Usage: RouteBoard input.dsn output.ses passes [ground-pours]");
        Freerouting.globalSettings = new GlobalSettings();
        Freerouting.globalSettings.usageAndDiagnosticData.disableAnalytics = true;
        RoutingJob job = new RoutingJob(UUID.randomUUID());
        job.setInput(args[0]);
        HeadlessBoardManager manager = new HeadlessBoardManager(null, job);
        manager.loadFromSpecctraDsn(job.input.getData(), null, new ItemIdentificationNumberGenerator());
        job.board = manager.get_routing_board();
        if (job.board == null) throw new IllegalStateException("DSN did not load");
        if (args.length == 4 && args[3].equals("ground-pours")) {
            var rules = job.board.rules;
            var defaults = rules.get_default_net_class();
            var ground = rules.append_net_class("NativeGroundPours");
            ground.set_via_rule(defaults.get_via_rule());
            ground.set_trace_clearance_class(defaults.get_trace_clearance_class());
            for (int layer=0; layer<ground.layer_count(); layer++)
                ground.set_trace_half_width(layer, defaults.get_trace_half_width(layer));
            ground.is_ignored_by_autorouter = true;
            for (var net : rules.nets.get("GND")) net.set_class(ground);
            System.out.println("Ground connectivity is deferred to native ground-pour refill.");
        }
        job.routerSettings = new RouterSettings(job.board);
        job.routerSettings.automatic_neckdown = false;
        job.routerSettings.set_stop_pass_no(Integer.parseInt(args[2]));
        job.state = RoutingJobState.RUNNING;
        job.thread = new StoppableThread() {
            protected void thread_action() { new BatchAutorouter(job).runBatchLoop(); }
        };
        job.thread.start();
        job.thread.join();
        Path output = Path.of(args[1]);
        try (var stream = Files.newOutputStream(output)) {
            if (!SpecctraSesFileWriter.write(job.board, stream, args[0]))
                throw new IllegalStateException("SES export failed");
        }
        if (Files.size(output) == 0) throw new IllegalStateException("Empty SES output");
        System.out.println("Saved routing session: " + output + " (" + Files.size(output) + " bytes)");
        System.exit(0);
    }
}
