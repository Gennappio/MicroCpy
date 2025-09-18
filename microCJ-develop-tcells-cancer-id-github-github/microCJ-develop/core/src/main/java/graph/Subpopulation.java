/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package graph;

import core.Cell;
import org.apache.commons.configuration2.HierarchicalConfiguration;
import org.apache.commons.configuration2.tree.ImmutableNode;

import java.util.*;
import java.util.stream.Collectors;

import static core.SettingsProvider.SETTINGS_PROVIDER;

/**
 * @author Pedro Victori
 */
public class Subpopulation {
	private final String name;
	private final String celltype;
	private final Map<String, Mutation> mutations = new HashMap<>();
	private final List<GeneExpressionSet> expressionSets = new ArrayList<>(); //if the same gene expression set is shared by all cells (i.e, not one per single cell) then this contains only 1 element
	private Iterator<GeneExpressionSet> setIterator;
	private int cellCount;
	private Double percent;
	private Integer initialCells;

	private Subpopulation(String name,String celltype) {
		this.name = name;
		this.celltype=celltype;
	}
	public String getName() {
		return name;
	}
	public String getCelltype() {
		return celltype;
	}

	public void changeCellCount(int change) {
		cellCount += change;
	}

	public int getCellCount() {
		return cellCount;
	}

	public Double getPercent() {
		return percent;
	}

	public Integer getInitialCells() {
		return initialCells;
	}

	/**
	 * Adds a cell to this Subpopulation
	 *
	 * @param cell the cell to be added to this Subpopulation
	 * @return  the cell identity, if single cell parameter is true, null otherwise.
	 */
	public String acceptCell(Cell cell) {
		Objects.requireNonNull(cell);
		cell.setSubpopulation(this);
		changeCellCount(1);
		String identity = null;
		if (!expressionSets.isEmpty()) {
			GeneExpressionSet set;
			if (expressionSets.size() > 1) { //if single cell
				if (setIterator == null) setIterator = expressionSets.iterator();
				set = setIterator.next();
				identity = set.getCellIdentities().get(0);
			} else {
				set = expressionSets.get(0);
			}
			cell.getNetwork().applyMutations(
					set.getAllTags().stream()
							.collect(Collectors.toMap(tag -> tag,
									tag -> Mutation.from(set, tag))));
		}
		cell.getNetwork().applyMutations(mutations);
		return identity;
	}

	public List<String> getIdentitiesInCluster(){
		if(SETTINGS_PROVIDER.getBoolean("gene-status-data.single-cell")){
			throw new IllegalStateException("Can't call this method if single cell parameter is true");
		}
		return expressionSets.get(0).getCellIdentities();
	}

	@Override
	public String toString() {
		return name;
	}

	public static List<Subpopulation> parseExpression() {
		boolean singleCell = SETTINGS_PROVIDER.getBoolean("gene-status-data.single-cell");
		boolean spatial = SETTINGS_PROVIDER.getBoolean("gene-status-data.spatial");
		String prefix = spatial ? "spatial_" : "";

		if (singleCell) {
			return GeneExpressionSet.parseSingleCellData(prefix).stream()
					.collect(Collectors.groupingBy(GeneExpressionSet::getSubpopulation, Collectors.toList()))
					.entrySet().stream().map(entry -> {
						var subpopulation = new Subpopulation(entry.getKey(),entry.getKey());//fix this later
						subpopulation.expressionSets.addAll(entry.getValue());
						subpopulation.initialCells = entry.getValue().size();
						return subpopulation;
					}).collect(Collectors.toList());
		} else {
			var clusterData = GeneExpressionSet.parseClusterData(prefix);
			if (spatial) { //keep initial counts
				return clusterData.entrySet().stream()
						.map(entry -> {
							var set = entry.getKey();
							var subpopulation = new Subpopulation(set.getSubpopulation(),set.getSubpopulation());//fix this later
							subpopulation.expressionSets.add(set);
							subpopulation.initialCells = entry.getValue();
							return subpopulation;
						}).collect(Collectors.toList());
			} else { //convert initial counts to percentages
				int totalN = clusterData.values().stream().mapToInt(value -> value).sum();
				return clusterData.entrySet().stream()
						.map(entry -> {
							var set = entry.getKey();
							var subpopulation = new Subpopulation(set.getSubpopulation(),set.getSubpopulation());//fix this later
							subpopulation.expressionSets.add(set);
							subpopulation.percent = (entry.getValue() * 100.) / totalN;
							return subpopulation;
						}).collect(Collectors.toList());
			}
		}
	}

	public static List<Subpopulation> parseExpressionWithMutations() {
		List<Subpopulation> subpopulations = parseExpression();
		var mutationsMap = parseMutationMap();
		for (Subpopulation subpopulation : subpopulations) {
			subpopulation.mutations.putAll(mutationsMap.getOrDefault(subpopulation.name, Collections.emptyMap()));
		}
		return subpopulations;
	}

	private static Map<List<String>, Map<String, Mutation>> parseMutationMap() {
		Map<List<String>, Map<String, Mutation>> mutationsMap = new HashMap<>();
		for (HierarchicalConfiguration<ImmutableNode> group : SETTINGS_PROVIDER.getSettings().configurationsAt("mutations.group")) {
			String name = group.getString("name");
			String celltype = group.getString("celltype");
			List<String> namecelltype= new ArrayList<>();
			namecelltype.add(name);
			namecelltype.add(celltype);
			Map<String, Mutation> mutations = group.configurationsAt("mutation").stream()
					.collect(Collectors.toMap(configNode -> configNode.getString("node"),
							configNode -> {
								int p = SETTINGS_PROVIDER.getGeneralString("network").strip().equals("prob") ?
										configNode.getInt("p", 1000) :
										1000;
								return new Mutation(configNode.getBoolean("sign"), p);
							}));
			mutationsMap.put(namecelltype, mutations);
		}
		return mutationsMap;
	}

	/**
	 * Parses the mutation settings and returns a List of all Subpopulations
	 *
	 * @return a List of Subpopulations
	 */
	public static List<Subpopulation> parseMutations() {
		List<Subpopulation> groupList = new ArrayList<>();
		var mutations = parseMutationMap();
		for (HierarchicalConfiguration<ImmutableNode> group : SETTINGS_PROVIDER.getSettings().configurationsAt("mutations.group")) {
			String name = group.getString("name");
			String celltype = group.getString("celltype");
			List<String> namecelltype= new ArrayList<>();
			namecelltype.add(name);
			namecelltype.add(celltype);
			double percent = group.getDouble("percent");
			var subpopulation = new Subpopulation(name, celltype);
			subpopulation.mutations.putAll(mutations.get(namecelltype));
			subpopulation.percent = percent;
			groupList.add(subpopulation);
		}
		return groupList;
	}
	public static Map<String,Integer> getCelltypeCellCount(List<Subpopulation> subpopulations, int initialnumber){
		double ca = 0;
		double cd = 0;
		for (Subpopulation subpopulation : subpopulations) {
			if(subpopulation.celltype.equals("cancer")){
				ca= ca + subpopulation.percent;
			}
			else if(subpopulation.celltype.equals("cd4")){
				cd = cd + subpopulation.percent;
			}
		}
		Map<String, Integer> celltypecellcount = new HashMap<>();
		celltypecellcount.put("cancer", (int)Math.round((ca*initialnumber)/100));
		celltypecellcount.put("cd4", (int)Math.round((cd*initialnumber)/100));
		return celltypecellcount;
	}


}
