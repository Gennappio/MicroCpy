package exp;

import core.World;
import stats.Stats;

import java.io.FileNotFoundException;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.StringJoiner;

/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
/**
 * Class for holding information related to a single world in a distributed multi-world scenario.
 * @author Pedro Victori
 */
class Experiment{
	private final List<World> worlds = new ArrayList<>();
	private final List<List<String>> allStats = new ArrayList<>();
	private String statsTitle;
	private final String tagPrefix;
	private Integer index;

	Experiment(String settingsFile, int iterations, int stepLimit, boolean td, String tag, boolean nl, Integer index) {
		this.index = index;
		if(index != null) {
			tag = tag + "_i" + index;
		}
		System.setProperty("exp.tag", tag);
		tagPrefix = tag.isEmpty() ? "" : tag + "_";
		if(nl) System.setProperty("tinylog.configuration", "tinylog_just-timepoints.properties");
		//create a World instance for each iteration
		for (int i = 0; i < iterations; i++) {
			World world = new World(settingsFile, stepLimit, index);
			world.setTag(tag);
			world.setup(true, td);
			worlds.add(world);
			if(statsTitle == null) statsTitle = world.getStatsTitle(); //all worlds would return the same value, so it just gets the first one
			world.whenFinished(() -> {
				allStats.add(world.getStatsLines());
				worlds.remove(world);
				if (worlds.isEmpty()) {
					saveStats();
					System.exit(0);
				}
			}); //adds a listener for when the simulation reaches the step limit
		}
	}

	void start() {
		for (World world : worlds) {
			world.start();
		}
	}

	/**
	 * Combines all stats in one file
	 */
	private void saveStats() {
		String fileName = tagPrefix + statsTitle +
				Stats.getNumberingForNextFile(statsTitle) +
				".csv";
		try(PrintWriter pw = new PrintWriter(fileName)){
			pw.println(allStats.get(0).get(0)); //prints header, they are all the same so the first one can be used for all
			allStats.stream().flatMap(stats -> {
				stats.remove(0); //remove header
				return stats.stream();
			}).forEach(pw::println);
		} catch (FileNotFoundException e) {
			e.printStackTrace();
		}
	}
}
