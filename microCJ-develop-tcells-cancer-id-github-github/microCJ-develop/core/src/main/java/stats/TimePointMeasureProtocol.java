package stats;

import core.Cell;
import core.World;
import diffusion.Diffusible;
import graph.Gene;
import graph.Node;

import java.util.*;
import java.util.stream.Collectors;

public enum TimePointMeasureProtocol {
	NODE_STATUS_BY_CELL(world -> {
		var measure = initialiseMapWithNodesByCell(world, false);
		for (Cell cell : world.getTumor().getCellList()) {
			if(cell.isAlive()){
				measure.computeIfAbsent("cell_id", s -> new ArrayList<>()).add("c"+cell.getId());
				measure.computeIfAbsent("subpopulation", s -> new ArrayList<>()).add(cell.getSubpopulationName().orElse("none"));

				for (Node node : cell.getNetwork().getNodes()) {
					measure.computeIfAbsent(node.getTag(), s -> new ArrayList<>()).add(node.isActive() ? "1" : "0");
				}
			}
		}

		return new TimePointMeasure(measure);
	}),

	GENE_RULES_BY_CELL(world -> {
		var measure = initialiseMapWithNodesByCell(world, true);
		for (Cell cell : world.getTumor().getCellList()) {
			if(cell.isAlive()){
				measure.computeIfAbsent("cell_id", s -> new ArrayList<>()).add("c"+cell.getId());
				measure.computeIfAbsent("subpopulation", s -> new ArrayList<>()).add(cell.getSubpopulationName().orElse("none"));

				for (Gene gene : cell.getNetwork().getGenes()) {
					measure.computeIfAbsent(gene.getTag(), s -> new ArrayList<>())
							.add(gene.getMutation().getProbString());
				}
			}
		}
		return new TimePointMeasure(measure);
	}),

	MUTATIONS_BY_CELL(world -> {
		var measure = initialiseMapWithNodesByCell(world, true);
		for (Cell cell : world.getTumor().getCellList()) {
			if(cell.isAlive()){
				measure.computeIfAbsent("cell_id", s -> new ArrayList<>()).add("c"+cell.getId());
				measure.computeIfAbsent("subpopulation", s -> new ArrayList<>()).add(cell.getSubpopulationName().orElse("none"));

				for (Gene gene : cell.getNetwork().getGenes()) {
					String mutation = gene.getMutation().isEmpty() ? "0" : gene.getMutation().toString();
					measure.computeIfAbsent(gene.getTag(), s -> new ArrayList<>()).add(mutation);
				}
			}
		}

		return new TimePointMeasure(measure);
	}),

	COORDINATES_BY_CELL(world -> {
		Map<String, List<String>> measure = new HashMap<>();
		for (Cell cell : world.getTumor().getCellList()) {
				measure.computeIfAbsent("cell_id", s -> new ArrayList<>()).add("c"+cell.getId());
				measure.computeIfAbsent("subpopulation", s -> new ArrayList<>()).add(cell.getSubpopulationName().orElse("none"));
				measure.computeIfAbsent("state", s -> new ArrayList<>()).add(cell.getState().toString().toLowerCase());
				measure.computeIfAbsent("i", s -> new ArrayList<>()).add(String.valueOf(cell.getLocation().getX()));
				measure.computeIfAbsent("j", s -> new ArrayList<>()).add(String.valueOf(cell.getLocation().getY()));
		}

		return new TimePointMeasure(measure);
	}),

	AGE_BY_CELL(world -> {
		Map<String, List<String>> measure = new HashMap<>();
		for (Cell cell : world.getTumor().getCellList()) {
			measure.computeIfAbsent("cell_id", s -> new ArrayList<>()).add("c"+cell.getId());
			measure.computeIfAbsent("subpopulation", s -> new ArrayList<>()).add(cell.getSubpopulationName().orElse("none"));
			measure.computeIfAbsent("age", s -> new ArrayList<>()).add(String.valueOf(cell.getAge()));
		}

		return new TimePointMeasure(measure);
	}),

	GENERATION_BY_CELL(world -> {
		Map<String, List<String>> measure = new HashMap<>();
		for (Cell cell : world.getTumor().getCellList()) {
			measure.computeIfAbsent("cell_id", s -> new ArrayList<>()).add("c"+cell.getId());
			measure.computeIfAbsent("subpopulation", s -> new ArrayList<>()).add(cell.getSubpopulationName().orElse("none"));
			measure.computeIfAbsent("generation", s -> new ArrayList<>()).add(String.valueOf(cell.getGeneration()));
		}

		return new TimePointMeasure(measure);
	}),

	CONCENTRATION_BY_VOXEL(world -> {
		List<Diffusible> diffusibles = world.getDiffusionModel().getDiffusibles();
		Map<String, Map<Diffusible, Double>> concentrationsPerVoxel = world.getDiffusionModel().getConcentrationsPerVoxel();
		Map<String, List<String>> measure = new HashMap<>();
		for (String voxel : concentrationsPerVoxel.keySet()) {
			String[] coords = voxel.split(",");
			measure.computeIfAbsent("i", s -> new ArrayList<>()).add(coords[0]);
			measure.computeIfAbsent("j", s -> new ArrayList<>()).add(coords[1]);
			if(!world.isTwoDim()) measure.computeIfAbsent("k", s -> new ArrayList<>()).add(coords[2]);

			Map<Diffusible, Double> concentrations = concentrationsPerVoxel.get(voxel);
			for (Diffusible diffusible : diffusibles) {
				measure.computeIfAbsent(diffusible.getName(), s -> new ArrayList<>()).add(Double.toString(concentrations.get(diffusible)));
			}
		}
		return new TimePointMeasure(measure);
	});

	private final TimePointMeasureTaker protocol;

	TimePointMeasureProtocol(TimePointMeasureTaker protocol) {
		this.protocol = protocol;
	}

	public TimePointMeasureTaker getProtocol() {
		return protocol;
	}

	private static Map<String, List<String>> initialiseMapWithNodesByCell(World world, boolean onlyGenes){
		Map<String, List<String>> measure = new HashMap<>();
		measure.put("cell_id", new ArrayList<>());
		measure.put("subpopulation", new ArrayList<>());
		var network =  world.getTumor().getCellList().stream()
				.filter(Cell::isAlive).findAny().orElseThrow().getNetwork();//to make sure we don't get a necrotic one with no network
		var nodes = (onlyGenes ? network.getGenes() : network.getNodes()).stream().map(Node::getTag).collect(Collectors.toSet());
		for (String node : nodes) {
			measure.put(node, new ArrayList<>());
		}

		return measure;
	}
}
