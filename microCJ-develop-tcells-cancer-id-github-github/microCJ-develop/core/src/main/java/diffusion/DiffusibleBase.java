/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */

package diffusion;

import core.SettingsProvider;
import org.apache.commons.configuration2.HierarchicalConfiguration;
import org.apache.commons.configuration2.tree.ImmutableNode;
import org.tinylog.Logger;

import java.util.ArrayList;
import java.util.List;

import static core.SettingsProvider.SETTINGS_PROVIDER;

/**
 * Base class for diffusible substances, with basic getters and a static method to import from csv
 * @author Pedro Victori
 */
public class DiffusibleBase implements Diffusible {
	private final String name;
	private final Double initialConcentration;
	private final Double diffusionCoefficient;
	private final Double threshold;
	private final Double defaultConsumption;
	private final String inputNode;
	private Double dt;

	DiffusibleBase(String name, String inputNode, Double initialConcentration, Double diffusionCoefficient, Double threshold, Double defaultConsumption) {
		this.name = name;
		this.initialConcentration = initialConcentration;
		this.diffusionCoefficient = diffusionCoefficient;
		this.threshold = threshold;
		if(defaultConsumption < 0) throw new IllegalArgumentException("Default consumption can't be under 0");
		this.defaultConsumption = defaultConsumption;
		this.inputNode = inputNode;
	}

	DiffusibleBase(Diffusible diffusible) {
		this(diffusible.getName(), diffusible.getInputNode(), diffusible.getInitialConcentration(),
				diffusible.getDiffusionCoefficient(), diffusible.getThreshold(), diffusible.getDefaultConsumption());
	}

	@Override
	public String getName() {
		return name;
	}

	@Override
	public Double getInitialConcentration() {
		return initialConcentration;
	}

	@Override
	public Double getDiffusionCoefficient() {
		return diffusionCoefficient;
	}

	@Override
	public Double getThreshold() {
		return threshold;
	}

	@Override
	public Double getDefaultConsumption() {
		return defaultConsumption;
	}

	@Override
	public String getInputNode() {
		return inputNode;
	}

	@Override
	public double getDt(){
		return dt;
	}

	@Override
	public void setDt(Double dt) {
		this.dt = dt;
	}

	@Override
	public boolean isOxygen(){
		return name.equalsIgnoreCase("oxygen");
	}

	public static List<Diffusible> parseDiffusibles(double dv) {
		List<Diffusible> list = new ArrayList<>();
		SettingsProvider s = SETTINGS_PROVIDER;
		double highestD = 0;
		for (HierarchicalConfiguration<ImmutableNode> diffusibleSetting : s.getSettings().configurationsAt("diffusibles.diffusible")) {

			Diffusible diffusible = new DiffusibleBase(
					s.getStringFromRawString(diffusibleSetting.getString("name")),
					s.getStringFromRawString(diffusibleSetting.getString("input-node")),
					s.getDoubleFromRawString(diffusibleSetting.getString("initial-concentration")),
					s.getDoubleFromRawString(diffusibleSetting.getString("diffusion-coefficient")),
					s.getDoubleFromRawString(diffusibleSetting.getString("threshold")),
					s.getDoubleFromRawString(diffusibleSetting.getString("consumption")));

			String type = diffusibleSetting.getString("type");

			switch (type) {
				case "nutrient":
					diffusible = new Nutrient(diffusible);
					break;
				case "factor":
					diffusible = new Factor(diffusible,
							s.getStringFromRawString(diffusibleSetting.getString("output-node")),
							s.getDoubleFromRawString(diffusibleSetting.getString("production")));
					break;
				case "drug":
					diffusible = new Drug(diffusible,
							s.getIntFromRawString(diffusibleSetting.getString("start-time")),
							s.getIntFromRawString(diffusibleSetting.getString("end-time")),
							s.getDoubleFromRawString(diffusibleSetting.getString("dose-concentration")));
					break;
				default:
					throw new IllegalArgumentException("Incorrect diffusible settings");
			}

			list.add(diffusible);
			if(diffusible.getDiffusionCoefficient() > highestD) highestD = diffusible.getDiffusionCoefficient();//store highest diffusion coefficient for calculation of dt.
			Logger.trace("Imported diffusible: {}", diffusible);
		}

		//set dt
		for (Diffusible diffusible : list) {
			double dt;
			double dv2 = Math.pow(dv, 2);
			if(diffusible.getDiffusionCoefficient() == highestD) {
				dt = 0.1 * dv2 / highestD;
			}
			else{
				dt = 0.1 * diffusible.getDiffusionCoefficient() / highestD;
			}
			diffusible.setDt(dt);
		}
		return list;
	}

	@Override
	public String toString() {
		return "DiffusibleBase{" +
				"name='" + name + '\'' +
				", initialConcentration=" + initialConcentration +
				", diffusionCoefficient=" + diffusionCoefficient +
				", threshold=" + threshold +
				", defaultConsumption=" + defaultConsumption +
				", inputNode='" + inputNode + '\'' +
				'}';
	}
}
