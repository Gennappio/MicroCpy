package core;

import geom.Point;
import graph.*;
import org.tinylog.Logger;
import update.Update;
import update.UpdateCollector;
import update.UpdateFlag;

import java.util.Optional;
import java.util.StringJoiner;

public abstract class Cell extends Identifier implements Agent {
	private static int arrestTime;
	private static NetworkType networkType;
	private static String initial;
	public final String celltype;
	public final String cellid;
	protected final String graphFile;
	protected final UpdateCollector updateCollector;
	protected Network network;
	protected double radius;
	private int age = 0;

	private int generation = 0;
	private CellState cellState = CellState.NORMAL;
	private int arrestCountdown;
	private Fate lastActivatedFate = Fate.NO_FATE_REACHED;
	private Subpopulation subpopulation;

	public Cell(double radius, String celltype, String graphFile, boolean randomiseDecisionWindow, UpdateCollector updateCollector, String cellid) {
		this.radius = radius;
		this.celltype = celltype;
		this.graphFile = graphFile;
		this.updateCollector = updateCollector;
		this.cellid = cellid;
		network = switch(networkType){
			case PROB -> ProbabilisticBooleanNetwork.randomlyActivatedGraph(graphFile, randomiseDecisionWindow, initial);
			case SYNC -> SynchronousBooleanNetwork.randomlyActivatedGraph(graphFile, randomiseDecisionWindow, initial);
			case ASYNC -> AsynchronousBooleanNetwork.randomlyActivatedGraph(graphFile, randomiseDecisionWindow, initial);
		};
		network.turnNode("oxygen_supply", true);
		network.update(); //update to map the nodes current state in this first run (see Network.update method body)
	}

	/**
	 * Return the cell's subpopulation inside an Optional. It is possible for the cell to not have a subpopulation, in which case it behaves as a wild type cell.
	 * @return an Optional Subpopulation
	 */
	public Optional<Subpopulation> getSubpopulation() {
		return Optional.ofNullable(subpopulation);
	}

	/**
	 * Return the cell's subpopulation name inside an Optional. It is possible for the cell to not have a subpopulation, in which case it behaves as a wild type cell.
	 * @return an Optional String
	 */
	public Optional<String> getSubpopulationName() {
		return getSubpopulation().map(Subpopulation::getName);
	}

	/**
	 * Sets the cell's subpopulation
	 * @param subpopulation the new subpopulation for the cell.
	 */
	public void setSubpopulation(Subpopulation subpopulation) {
		if (subpopulation != null) {
			this.subpopulation = subpopulation;
		}
	}

	public CellState getState() {
		return cellState;
	}

	/**
	 * Whether the cell is alive or not. Alive means that its state is neither DEAD nor NECROTIC.
	 * @return true if the cell is alive, false otherwise.
	 */
	public boolean isAlive() {
		return cellState != CellState.DEAD && cellState != CellState.NECROTIC;
	}

	/**
	 * Whether the cell is necrotic or not
	 * @return true is the cell is necrotic, false otherwise
	 */
	public boolean isNecrotic(){
		return cellState == CellState.NECROTIC;
	}

	/**
	 * Returns the cell's radius
	 * @return the cell's radius
	 */
	public double getRadius() {
		return radius;
	}

	/**
	 * Sets a new radius value
	 * @param radius the value for the new radius
	 */
	public void setRadius(double radius) {
		this.radius = radius;
	}

	/**
	 * Returns the cell's age
	 * @return the cell's Age
	 */
	public int getAge() {
		return age;
	}

	public int getGeneration() {
		return generation;
	}

	/**
	 * Returns the cell's network
	 * @return the cell's network
	 */
	public Network getNetwork() {
		return network;
	}

	private void resetArrestCountdown() {
		arrestCountdown = arrestTime;
	}

	public boolean isArrested() {
		return cellState.equals(CellState.ARRESTED);
	}

	public boolean isNormal() {
		return cellState.equals(CellState.NORMAL);
	}

	void arrest() {
		if(!isArrested()) { //only do anything if the cell is not already arrested
			lastActivatedFate = Fate.GROWTH_ARREST; //in case a proliferation is replaced by growth arrest because of lack of space.
			resetArrestCountdown();
			cellState = CellState.ARRESTED;
		}
	}



	void apoptose(){
		cellState = CellState.DEAD;
		triggerUpdate(UpdateFlag.DEAD_CELL);
	}

	void necrotize() {
		cellState = CellState.NECROTIC;
		triggerUpdate(UpdateFlag.NECROTIC_CELL);
	}

	/**
	 * Ask the cell's gene graph to compute a new Fate decision for the cell.
	 * @return A Fate object with the decision reached.
	 */
	public Fate update(){
		age++;
		if (! isAlive()) return Fate.NO_FATE_REACHED; //no update to compute if cell is dead
		if(isArrested()){
			arrestCountdown();
		}
		if(cellState.equals(CellState.ARRESTED)) return Fate.GROWTH_ARREST;
		lastActivatedFate = getNetwork().update();
		if(lastActivatedFate == Fate.APOPTOSIS && generation == 0 && age < 5){
			lastActivatedFate = Fate.NO_FATE_REACHED;
		}
		Logger.debug("{} Cell {} updated, fate: {}", subpopulation.getName(), getId(), lastActivatedFate);
		return lastActivatedFate;
	}

	private void arrestCountdown() {
		arrestCountdown--;
		if (arrestCountdown == 0) {
			resetArrestCountdown();
			cellState = CellState.NORMAL;
		}
	}

	/**
	 * Activates an input node in the gene graph after consumption of the required substance during diffusion simulation.
	 * @param input The name of the input node to be activated in the gene network.
	 */
	public void consume(String input) {
		getNetwork().turnNode(input, true);
	}

	/**
	 * If an input substance has not been consumed during the diffusion simulation, the corresponding input node will be turned off.
	 * @param input The name of the input node to be deactivated in the gene network
	 */
	public void starve(String input) {
		getNetwork().turnNode(input, false);
	}

	/**
	 * Queries the gene graph to see if the specified Node is active, providing the cell is alive
	 * @param outputNode The name of the node to be checked.
	 * @return True if the node is active and the cell is alive, false otherwise.
	 */
	public boolean isExpressing(String outputNode) {
		if(!isAlive()) return false;
		else return getNetwork().isNodeActive(outputNode);
	}

	public Fate getLastActivatedFate() {
		return lastActivatedFate;
	}

	private void triggerUpdate(UpdateFlag flag) {
		updateCollector.collect(new Update<>(flag, this)); //lets the collector (from World) know that there is a new update, so it will be added to the global queue
	}

	@Override
	public String getInfo() {
		return new StringJoiner(System.lineSeparator())
				.add("Cell ").add(getId().toString())
				.add("Age: ").add(Integer.toString(age))
				.add("State: ").add(cellState.toString())
				.add("Last Activated Fate: ").add(lastActivatedFate.toString())
				.add("Subpopulation: ").add(getSubpopulationName().orElse("none"))
				.add("Coordinates: " + getLocation().toUserString())
				.toString();
	}

	@Override
	public String toString() {
		return "Cell[id: " + getId() +
				"state: " + cellState.toString() +
				", subpopulation: " + getSubpopulationName().orElse("none") +
				", position: " + getLocation().toUserString() + "]";
	}

	public abstract Point getLocation();
	/**
	 * Creates a new instance of Cell that is a copy of this Cell.
	 * @return A copy of this Cell.
	 */
	public final Cell copy(){
		Cell copy = createCopy();
		copy.setSubpopulation(getSubpopulation().orElse(null));
		copy.getNetwork().applyMutations(getNetwork().gatherMutations());
		copy.generation = generation + 1;
		return copy;
	}

	/**
	 * Generates a copy of this Cell, to be implemented by subclasses.
	 */
	protected abstract Cell createCopy();
	static void setArrestTime(int time){
		arrestTime = time;
	}

	public static void setNetworkType(NetworkType networkType) {
		Cell.networkType = networkType;
	}

	public static void setInitial(String initial) {
		Cell.initial = initial;
	}
	public String getCelltype() {
		return this.celltype;
	}
}
