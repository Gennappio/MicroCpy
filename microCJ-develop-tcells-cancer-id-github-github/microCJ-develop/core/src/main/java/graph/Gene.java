/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package graph;

import core.Identifier;
import org.tinylog.Logger;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;

/**
 * @author Pedro Victori
 */
public class Gene extends Identifier implements Node {
    private final String tag;
    private boolean active;
    private final List<Rule> rules = new ArrayList<>();
    private Mutation mutation = new Mutation(null, 0);

    protected Gene(String tag){
        this.tag = tag;
    }

    private boolean drugTaken = false;

    public Gene(String tag, String rule) {
        this.tag = tag;
        rules.add(Rule.parser(rule));
    }

    public Gene(String tag, List<Rule> rules){
        this.tag = tag;
        this.rules.addAll(rules);
    }

    @Override
    public String getTag() {
        return tag;
    }

    @Override
    public void setActive(boolean active) {
        this.active = mutation.accountForMutation().orElse(active) && !drugTaken;
        drugTaken = false;
    }

    /* mutations should not override drug exposure. This is a temporary implementation while I design something
more generic.
TODO generalisable implementation
*/
    void drugTaken(Map<String, Boolean> values) {
        //if true, mutation won't be taken into account
        drugTaken =
                (tag.equals("EGFR") && (values.getOrDefault("EGFR_TKI", false) ||
                        values.getOrDefault("anti_EGFR_mAb", false) ||
                        values.getOrDefault("TKI", false))) ||
                (tag.equals("AXL") && values.getOrDefault("AXLi", false))||
                (tag.equals("EGR1") && values.getOrDefault("EGR1i", false))||
                (tag.equals("PI3K") && values.getOrDefault("PI3Ki", false))||
                (tag.equals("MET") && values.getOrDefault("METi", false))||
                (tag.equals("IGF1R") && values.getOrDefault("IGF1Ri", false));
    }

    @Override
    public boolean isActive() {
        return active;
    }

    /**
     * Compute the new state for the gene
     * @param values the state of all the nodes in the network
     * @return a boolean representing activation status
     */
    @Override
    public boolean computeState(Map<String, Boolean> values){
        return chooseRule().computeRule(values);
    }

    private Rule chooseRule(){
        if(rules.size() == 1) return rules.get(0);
        int r = ThreadLocalRandom.current().nextInt(1000);
        int limit = 0;
        for (Rule rule : rules) {
            limit += rule.getP();
            if(r < limit){
                Logger.debug("Gene {} chooses rule {} with r {}", tag, rule, r);
                return rule;
            }
        }
        throw new IllegalStateException("There's a problem with rule probabilities");
    }

    public void applyMutation(Mutation mutation) {
        this.mutation.add(mutation);
    }

    @Override
    public NodeType getNodeType() {
        return NodeType.GENE;
    }

    public Mutation getMutation() {
            return mutation;
    }

    @Override
    public String toString() {
        return tag + ", active: " + isActive() + ", mutation: " + mutation;
    }
}
