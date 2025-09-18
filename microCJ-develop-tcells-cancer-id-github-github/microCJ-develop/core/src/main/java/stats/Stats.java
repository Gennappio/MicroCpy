/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package stats;

import core.SettingsProvider;
import core.World;
import org.apache.commons.configuration2.HierarchicalConfiguration;
import org.apache.commons.configuration2.tree.ImmutableNode;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.PrintWriter;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static core.SettingsProvider.SETTINGS_PROVIDER;
import static java.util.stream.Collectors.toList;

/**
 * Class that stores a series of measures taken during the simulation, along with the functions to take those measures. The exact measures
 * that will be taken are defined in the general settings file, parsed by the World object.
 * @author Pedro Victori
 */
public class Stats {
	private final String filename;
	private final String numbering;
	private final boolean writeFileOnTheGo;
	private final List<String> lines = new ArrayList<>();
	private final Map<MeasureProtocol, List<String>> protocols = new HashMap<>();
	private int timePoint = 0;
	private PrintWriter printWriter;
	private final String tag;

	private final Map<Integer, List<TimePointMeasureProtocol>> timePointProtocols = new HashMap<>();

	/**
	 * Creates a new instance of Stats, with the specified filename and the relevant configuration excerpt from the general settings
	 * @param filename the name for the final CSV file that will be created containing all the measures.
	 * @param tag
	 */
	public Stats(String filename, boolean writeFileOnTheGo, String tag) {
		this.filename = filename;
		numbering = getNumberingForNextFile(filename);
		this.writeFileOnTheGo = writeFileOnTheGo;
		this.tag = tag == null ? "" : tag + "_";
		for (HierarchicalConfiguration<ImmutableNode> stat : SETTINGS_PROVIDER.getSettings().configurationsAt("stats.stat")) {
			MeasureProtocol protocol = MeasureProtocol.valueOf(stat.getString("").strip().toUpperCase());
			Stream<String> option = protocol.needsOption() ? Stream.of(stat.getString("[@option]")) : Stream.empty();
			protocols.compute(protocol,(measureProtocol, options) ->
					options == null ? option.collect(toList()) : Stream.concat(options.stream(), option).collect(toList())); //saves options associated to this protocol in a map for later retrieval
		}

		//time point stats
		for (HierarchicalConfiguration<ImmutableNode> stat : SETTINGS_PROVIDER.getSettings().configurationsAt("timepoint-stats.stat")) {
			var protocol = TimePointMeasureProtocol.valueOf(stat.getString("type").strip().toUpperCase());
			if (protocol.equals(TimePointMeasureProtocol.GENE_RULES_BY_CELL) && !SETTINGS_PROVIDER.getBoolean("gene-status-data.parse")) {
				throw new IllegalStateException("gene_rules_by_cell is only to be used if gene expression datasets are being imported");
			}
			var timepointConfig = stat.configurationsAt("timepoint");
			String value = timepointConfig.get(0).getString("").strip();
			String pattern = "\\[(\\d+)-(\\d+),(\\d+)]";
			Pattern r = Pattern.compile(pattern);
			Matcher m = r.matcher(value);
			if (m.find()) {
				int start = Integer.parseInt(m.group(1));
				int end = Integer.parseInt(m.group(2));
				int period = Integer.parseInt(m.group(3));
				for (int i = start; i <= end; i += period) {
					timePointProtocols.computeIfAbsent(i, integer -> new ArrayList<>()).add(protocol);
				}
			} else {
				for (var timePointStat : timepointConfig) {
					timePointProtocols
							.computeIfAbsent(Integer.valueOf(timePointStat.getString("").strip()), integer -> new ArrayList<>())
							.add(protocol);
				}
			}
		}
	}

	/**
	 * Takes all the instance-specific measures of the given world, and writes a new line in the file with them
	 * @param world the world instance to take measures from
	 * @param step
	 */
	public void takeMeasures(World world, int step) {
		List<Measure> currentMeasures = new ArrayList<>();

		for (MeasureProtocol protocol : protocols.keySet()) {
			if (protocol.needsOption()) {
				for (String option : protocols.get(protocol)) {
					currentMeasures.add(protocol.getMeasuringProcedure().take(world, option));
				}
			}
			else currentMeasures.add(protocol.getMeasuringProcedure().take(world, null));
		}

		//before new line, checks if header has been added
		if (lines.isEmpty()) {
			String header = "time point," + currentMeasures.stream().map(Measure::getHeader).collect(Collectors.joining(",")); //headers to csv, adds a header for time points
			lines.add(header);

			if(writeFileOnTheGo) {
				try {
					printWriter = new PrintWriter(tag + filename + numbering + ".csv");
					printWriter.println(header);
				} catch (FileNotFoundException e) {
					e.printStackTrace();
				}
			}
		}

		String newLine = timePoint++ + ","
				+ currentMeasures.stream().map(Measure::getValue).collect(Collectors.joining(","));
		lines.add(newLine);
		//new line to file
		if(writeFileOnTheGo) printWriter.println(newLine);

		//check if this is a time point where a stat has to be taken
		if(timePointProtocols.containsKey(step)){
			var protocols = timePointProtocols.get(step);
			for (TimePointMeasureProtocol protocol : protocols) {
				var measure = protocol.getProtocol().take(world).measure();
				int n = measure.values().stream().findAny().orElseThrow().size(); //all lists are the same size
				try {
					PrintWriter tpw = new PrintWriter(tag + protocol.toString().toLowerCase() + "_t" + step + getNumberingForNextFile(filename) + ".csv");
					List<String> columns = new ArrayList<>(measure.keySet());
					tpw.println(String.join(",", columns)); //print header
					for (int i = 0; i < n; i++) {
						StringJoiner joiner = new StringJoiner(",");
						for (String column : columns) {
							joiner.add(measure.get(column).get(i));
						}
						tpw.println(joiner);
					}
					tpw.close();

				} catch (FileNotFoundException e) {
					e.printStackTrace();
				}
			}
		}
	}

	public List<String> getLines() {
		return lines;
	}

	/**
	 * Closes the Writer used to write the stats file, needed to save memory.
	 */
	public void finish() {
		printWriter.close();
	}

	public static String getNumberingForNextFile(String filename){
		File dir = new File(".");
		var files = dir.listFiles();
		int index = Arrays.stream(files)
				.filter(file -> file.getName().startsWith(filename))
				.mapToInt(file ->
						Integer.parseInt(file.getName()
								.split("[_.]")[1]))
				.max().orElse(0); //returns 0 if the stream is empty
		return "_" + (index + 1);
	}
}

