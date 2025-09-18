/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package core;

import geom.Distributor;
import geom.Point;
import geom.threeDim.*;
import geom.twoDim.*;
import graph.Subpopulation;
import org.tinylog.Logger;
import update.Updatable;
import update.Update;
import update.UpdateCollector;
import update.UpdateFlag;
import graph.FBA;

import java.util.*;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.stream.Collectors;

import static core.SettingsProvider.SETTINGS_PROVIDER;

/**
 * Class for holding references to all cells and dealing with the update of their state.
 *
 * @author Pedro Victori
 */

public class Tumor {
	private final List<Cell> cellList = new ArrayList<>();
	private final Point3D center;
	private final List<Subpopulation> subpopulations;
	private final UpdateCollector updateCollector;
	private final double mutationChance;
	private final boolean twoDim;
	private final boolean shoving;
	private final int initialNumber;
	private final int initialNumbercancer;
	private final int initialNumbercd4;
	private final Distributor distributor;
	private final Queue<Cell> proliferationQueue = new ConcurrentLinkedQueue<>();
	public static Map<String, String> fbadata;

	private Map<Subpopulation, Integer> deadCellsAtLastStep = new HashMap<>();

	Tumor(List<Subpopulation> subpopulations, Point3D center, UpdateCollector updateCollector, boolean twoDim) {
		this.center = center;
		this.subpopulations = subpopulations;
		this.updateCollector = updateCollector;
		this.shoving = SETTINGS_PROVIDER.getGeneralBoolean("shoving");
		this.mutationChance = SETTINGS_PROVIDER.getGeneralDouble("random-mutations");
		this.twoDim = twoDim;

		boolean singleCell = SETTINGS_PROVIDER.getBoolean("gene-status-data.single-cell");
		boolean spatial = SETTINGS_PROVIDER.getBoolean("gene-status-data.spatial");
		double cellRadius = SETTINGS_PROVIDER.getGeneralDouble("cell-radius");

		this.initialNumber = (singleCell || spatial) ?
				subpopulations.stream().mapToInt(Subpopulation::getInitialCells).sum() :
				SETTINGS_PROVIDER.getGeneralInt("starting-cells");

		this.initialNumbercancer = Subpopulation.getCelltypeCellCount(this.subpopulations,initialNumber).get("cancer");
		this.initialNumbercd4 = Subpopulation.getCelltypeCellCount(this.subpopulations,initialNumber).get("cd4");


		//determine the location for every cell
		String distributor2DType = SETTINGS_PROVIDER.getGeneralString("distributor-2d");
		String distributor3DType = SETTINGS_PROVIDER.getGeneralString("distributor-3d");
		boolean cachePositions = SETTINGS_PROVIDER.getGeneralBoolean("cache-positions");
		double gap = cellRadius * 2;

		String fbafile = SETTINGS_PROVIDER.getGeneralString("fba-file");
		this.fbadata = FBA.loadFBA(fbafile);
		List<String> cancercellids = FBA.getCellId(fbadata);
		int setinitialnumber = cancercellids.size();

		distributor = spatial ? new ImporterDistributor(gap) :
				selectDistributor(twoDim ? distributor2DType : distributor3DType, gap, cachePositions);
		distributor.populate(initialNumber);

		String graphFile = SETTINGS_PROVIDER.getGeneralString("graph-file");
		String cancergraphFile = SETTINGS_PROVIDER.getGeneralString("cancer-graph-file");
		String cd4graphFile = SETTINGS_PROVIDER.getGeneralString("cd4-graph-file");
		String cancer = "cancer";
		String cd4 = "cd4";
		String cellid = "cellid";
		if (twoDim) {
			if (spatial) {
				//in spatial data simulations, cells will be given a location along with their subpopulation and identity
				int total = distributor.getTotal();
				for (int i = 0; i < total; i++) {
					cellList.add(new Cell2D(cellRadius, cancer, graphFile,
							true, updateCollector,cellid));
				}
			} else {
				int i=0;
				var distributor2D = (Distributor2D) distributor;
				for (Point2D location : distributor2D.getLocations()) { //create all initial cells
					if(i<setinitialnumber && initialNumbercancer>0) {
						String cancercellid = cancercellids.get(i);
						cellList.add(new Cell2D(location, cancer, cellRadius, cancergraphFile,
								true, updateCollector,cancercellid));
						i++;
					} else{
						cellid = cellid + i;
						cellList.add(new Cell2D(location, cd4, cellRadius, cd4graphFile,
								true, updateCollector,cellid));
						i++;
					}
				}
			}
		} else {
			//noinspection ConstantConditions: can't be spatial and 3D because of settings rule enforcement in World.
			var distributor3D = (Distributor3D) distributor;
			for (Point3D location : distributor3D.getLocations()) { //create all initial cells
				for (int i = 0; i < this.initialNumbercancer; i++) {
					cellList.add(new Cell3D(location, cellRadius, cancer, cancergraphFile,
							true, updateCollector, cellid));
				}
				for (int i = 0; i < this.initialNumbercd4; i++) {
					cellList.add(new Cell3D(location, cellRadius, cd4, cd4graphFile,
							true, updateCollector,cellid));
				}
			}
		}

		if (!spatial && !SETTINGS_PROVIDER.getGeneralBoolean("close-group-placement")) Collections.shuffle(cellList);

		Queue<Cell> cellsWaitingForGroup = new LinkedList<>(cellList);//put all cells from cell list into a queue to wait to receive their mutation group

		for (Subpopulation subpopulation : subpopulations) {
			int nCells = Objects.requireNonNullElseGet(subpopulation.getInitialCells(),
					() -> (int) Math.ceil((subpopulation.getPercent() * initialNumber) / 100));
			for (int i = 0; i < nCells; i++) {
				Cell nextCell = cellsWaitingForGroup.poll();
				if (nextCell == null) {
					break; //nextCell will be null if the queue was empty, so we can finish the loop
				}
				if (subpopulation.getCelltype().equals(nextCell.celltype)){
					String identity = subpopulation.acceptCell(nextCell); // identity will be null unless (single cell), only needed if (spatial)
					if (spatial) {
						Map<String, Point2D> locationsMap = ((ImporterDistributor) distributor).getMap();
						Cell2D nextCell2D = (Cell2D) nextCell;
						if (singleCell) {
							nextCell2D.setLocation(locationsMap.get(identity));
						} else {
							nextCell2D.setLocation(locationsMap.get(subpopulation.getIdentitiesInCluster().get(i)));
						}
					}
				} else {
					cellsWaitingForGroup.offer(nextCell);
					i--;
				}
			}
		}
	}

	private Distributor selectDistributor(String setting, double gap, boolean cache) {
		if (twoDim) {
			return switch (setting) {
				case "random" -> new RandomDistributor2D(gap, shoving);
				case "hexagonal" -> new RegularDistributor2D(gap, shoving, DistributionType.HEXAGONAL);
				case "square" -> new RegularDistributor2D(gap, shoving, DistributionType.SQUARE);
				default -> throw new IllegalStateException("Wrong setting for 2D distributor");
			};
		} else {
			if (setting.equals("random")) return new RandomDistributor3D(gap, cache);
			else if (setting.equals("square")) return new SquareDistributor3D(gap, cache);
			else if (setting.equals("hexagonal")) return new HexagonalDistributor3D(gap, cache);
			else throw new IllegalStateException("Wrong setting for 3D distributor");
		}

	}


	public List<Cell> getCellList() {
		return cellList;
	}
	public List<Cell> getcelltypeCellList(String celltype) {
		List<Cell> celltypelist = new ArrayList<>();
		for(Cell cell:cellList){
			if(cell.celltype == celltype){
				celltypelist.add(cell);
			}
		}
		return celltypelist;
	}

	public int getInitialNumber() {
		return initialNumber;
	}

	public List<Subpopulation> getMutationGroups() {
		return subpopulations;
	}
	public List<Subpopulation> getCellTypes() {
		List<Subpopulation> celltypes = new ArrayList<>();
		return celltypes;
	}

	void tickAllCells() {
		deadCellsAtLastStep.clear();
		cellList.parallelStream().forEach(cell -> cell.update().getExecutionRule().execute(cell, this));
		Logger.info("cells ticked");
		Logger.info("starting proliferation");
		while (proliferationQueue.size() > 0) {
			proliferate(proliferationQueue.poll());
		}
		Logger.info("proliferation done");
	}

	/**
	 * Makes the necessary changes to the cell list.
	 * Doing it after the update step guarantees that there are not co-modification issues and the updating order doesn't matter
	 */
	void executeUpdate(Update<UpdateFlag, Updatable> update) {
		switch (update.getFlag()) {
			case DEAD_CELL:
				//This is done after new cells have already been located, so the order in which cells are looped doesn't matter
				Cell cell = (Cell) update.getUpdatable();
				distributor.remove(cell.getLocation());
				cellList.remove(cell);
				cell.getSubpopulation().ifPresent(mutationGroup -> mutationGroup.changeCellCount(-1));
				deadCellsAtLastStep.merge(cell.getSubpopulation().get(), 1, Integer::sum);
				break;
			case NECROTIC_CELL:
				//nothing to do
				break;
			case NEW_CELL:
				cellList.add((Cell) update.getUpdatable());
				break;
		}
		Logger.trace("update {} executed", update.getFlag());
	}

	public Map<Subpopulation, Integer> getDeadCellsAtLastStep() {
		return deadCellsAtLastStep;
	}

	void addToProliferationQueue(Cell cell) {
		Logger.debug("Cell {} offering to proliferation queue", cell.getId());
		proliferationQueue.offer(cell);
		Logger.debug("Cell {} added to proliferation queue", cell.getId());
	}

	/**
	 * Checks if there is available space next to the cell, if so it creates a copy  of the cell and places it next to the original cell.
	 *
	 * @param cell the original cell to be copied
	 */
	private void proliferate(Cell cell) {
		Logger.debug("starting proliferation of cell {}", cell.getId());
		Point location = distributor.locateEmptySpotNextTo(cell.getLocation());
		if (location != null || shoving) { //if there's free space next to this cell or shoving is active
			Cell newCell = cell.copy();
			if (mutationChance > 0) {
				newCell.getNetwork().mutate(mutationChance);
			}
			if (twoDim) {
				var distributor2D = (Distributor2D) distributor;
				var cell2D = (Cell2D) cell;
				if (shoving && location == null)
					location = distributor2D.getArbitraryPointNextTo(cell2D.getPoint2D());
				var location2d = (Point2D) location;
				((Cell2D) newCell).setLocation(location2d);
				distributor2D.getLocations().add(location2d);
			} else {
				var distributor3D = (Distributor3D) distributor;
				var cell3D = (Cell3D) cell;
				if (shoving && location == null)
					location = distributor3D.getArbitraryPointNextTo(cell3D.getPoint3D());
				var location3d = (Point3D) location;
				((Cell3D) newCell).setLocation(location3d);
				distributor3D.getLocations().add(location3d);
			}
			//to be added to update queues
			updateCollector.collect(new Update<>(UpdateFlag.NEW_CELL, newCell));
			Logger.debug("proliferation of cell {} done", cell.getId());
		} else {
			cell.arrest(); //if there is no space to proliferate, the cell goes into cell arrest.
		}
	}

	void shove() {
		if (twoDim) {
			var distributor2D = (Distributor2D) distributor;
			List<Point2D> oldLocations = new ArrayList<>(distributor2D.getLocations());
			distributor2D.shove();
			for (Cell cell : cellList) {
				var cell2D = (Cell2D) cell;
				int i = oldLocations.indexOf(cell2D.getPoint2D()); //locate position of cell location in locations list to get the new location.
				cell2D.setLocation(distributor2D.getLocations().get(i));
			}
		} else {
			var distributor3D = (Distributor3D) distributor;
			List<Point3D> oldLocations = new ArrayList<>(distributor3D.getLocations());
			distributor3D.shove();
			for (Cell cell : cellList) {
				var cell3D = (Cell3D) cell;
				int i = oldLocations.indexOf(cell3D.getPoint3D()); //locate position of cell location in locations list to get the new location.
				cell3D.setLocation(distributor3D.getLocations().get(i));
			}
		}
	}

	//info methods

	/**
	 * Returns the total number of cells, including dead ones (necrotic cells, and apoptotic cells during the instant in which they have still not been eliminated from the simulation).
	 *
	 * @return the total number of cells as an int.
	 */
	public int getTotalCount() {
		return cellList.size();
	}
	public int getTotalCancerCount(){
		List<Cell> cancerCellList = new ArrayList<>();
		for(Cell cell : cellList){
			if("cancer".equals(cell.getCelltype())){
				cancerCellList.add(cell);
			}
		}
		return cancerCellList.size();
	}
	public int getTotalcd4Count(){
		List<Cell> cd4CellList = new ArrayList<>();
		for(Cell cell : cellList){
			if("cd4".equals(cell.getCelltype())){
				cd4CellList.add(cell);
			}
		}
		return cd4CellList.size();
	}


	/**
	 * Returns the total number of alive cells, this is all cells excluding necrotic and apoptotic cells.
	 *
	 * @return the total number of alive cells as an int.
	 */
	public int getTotalAliveCount() {
		List<Cell> snapshot = new ArrayList<>(cellList);
		return (int) snapshot.stream().filter(Cell::isAlive).count();
		/**
		return (int) cellList.stream().filter(Cell::isAlive).count();
		 */
	}
	public int getTotalCancerAliveCount(){
		List<Cell> cancerAliveCellList = new ArrayList<>();
		for(Cell cell : cellList.stream().filter(Cell::isAlive).collect(Collectors.toList())){
			if("cancer".equals(cell.getCelltype())){
				cancerAliveCellList.add(cell);
			}
		}
		return cancerAliveCellList.size();
	}
	public int getTotalcd4AliveCount(){
		List<Cell> cd4AliveCellList = new ArrayList<>();
		for(Cell cell : cellList.stream().filter(Cell::isAlive).collect(Collectors.toList())){
			if("cd4".equals(cell.getCelltype())){
				cd4AliveCellList.add(cell);
			}
		}
		return cd4AliveCellList.size();
	}
	/**
	 * Returns a list of all the subpopulation names
	 *
	 * @return a List of String with all the subpopulation names.
	 */
	public List<String> getSubpopulationNames() {
		return subpopulations.stream().map(Subpopulation::getName).collect(Collectors.toList());
	}

	/**
	 * Returns a Map containing the total cell count per subpopulation. This count includes dead cells.
	 *
	 * @return a Map of subpopulation names as String keys and cell counts as int values.
	 */
	public Map<String, Integer> getSubpopulationCounts() {
		return subpopulations.stream().collect(Collectors.toMap(Subpopulation::getName, Subpopulation::getCellCount));
	}

	/**
	 * Returns a Map containing the total alive cells count per subpopulation. This count excludes dead cells
	 *
	 * @return a Map of subpopulation names as String keys and cell counts as int values.

	public Map<String, Integer> getSubpopulationAliveCounts() {
		return subpopulations.stream().collect(Collectors.toMap(Subpopulation::getName,
				mutationGroup -> (int) cellList.stream().filter(Cell::isAlive)
						.filter(cell -> Objects.equals(cell.getSubpopulation().orElse(null), mutationGroup)).count()));
	}
	 */

	public Map<String, Integer> getSubpopulationAliveCounts() {
		List<Cell> cellListSnapshot = new ArrayList<>(cellList); // Create a snapshot
		List<Subpopulation> subpopulationsSnapshot = new ArrayList<>(subpopulations); // Create a snapshot

		return subpopulationsSnapshot.stream().collect(Collectors.toMap(Subpopulation::getName,
				mutationGroup -> (int) cellListSnapshot.stream().filter(Cell::isAlive)
						.filter(cell -> Objects.equals(cell.getSubpopulation().orElse(null), mutationGroup)).count()));
	}

}
