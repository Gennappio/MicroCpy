/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package exp;

import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Parameters;
import picocli.CommandLine.Option;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.Callable;

/**
 * Class for launching the CLI
 * @author Pedro Victori
 */
@Command(name = "microcj", mixinStandardHelpOptions = true, version = "0.3",
		footer = {"MicroCJ created by Pedro Victori (Buffa lab)",
				"Released under the Apache License 2.0.",
				"https://github.com/CBigOxf/microCJ",
				"https://www.oncology.ox.ac.uk/team/francesca-buffa"},
		description = "A 3D, multilevel agent-based tumour modelling framework.")
class McjCli implements Callable<Void> {
	@Option(names = "--td", description = "Whether the simulation will be run in two dimensions. If this option is not included, then the simulation will be run in three dimensions")
	private boolean td;
	@Option(names = "-nl", description = "Perform no logging but for timepoints.")
	private boolean nl;

	@Option(names = "-i", description = "An 0-based index for when the settings contains a sensitivity analysis")
	private Integer index;

	@Parameters(hidden = true)  // "hidden": don't show this parameter in usage help message
			List<String> allParameters; // no "index" attribute: captures _all_ arguments (as Strings)
	@Parameters(index = "0", description = "the name of the xml file containing the desired settings")
	private String settings;
	@Parameters(index = "1", description = "number of simulations to be run") private int iterations;
	@Parameters(index = "2", description = "number of steps each simulation will run for") private int steps;
	@Parameters(index = "3", defaultValue = "", description = "an optional tag for the experiment that will be used in output files") private String tag;

	private boolean aboutRequested; //todo implement

	public static void main(String[] args) {
		System.out.println("args" + Arrays.toString(args));
		new CommandLine(new McjCli()).execute(args);
	}

	@Override
	public Void call() {
		if(aboutRequested) System.out.println("MicroCJ created by Pedro Victori (Buffa lab) \n" +
				"Released under the Apache License 2.0. \n" +
				"https://github.com/CBigOxf/microCJ \n" +
				"https://www.oncology.ox.ac.uk/team/francesca-buffa");
		Experiment experiment = new Experiment(settings, iterations, steps, td, tag, nl, index);
		experiment.start();
		return null;
	}
}
