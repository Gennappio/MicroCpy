package core;

/**
 * An enumeration for listing the Cell possible states.
 */
public enum CellState {
	NORMAL, //functioning as default
	ARRESTED, //will be unresponsive for an interval of time
	NECROTIC, //is dead but still occupying space
	DEAD //is dead and will be removed from the simulation as soon as possible
}
